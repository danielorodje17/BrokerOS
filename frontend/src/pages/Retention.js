import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const MORTGAGE_TYPES = [
  { value: 'remortgage', label: 'Remortgage' },
  { value: 'product_transfer', label: 'Product Transfer' },
  { value: 'residential', label: 'Residential' },
  { value: 'btl', label: 'Buy to Let' },
  { value: 'bridging', label: 'Bridging' },
];

const STATUS_LABELS = {
  none: { label: 'Monitoring', bg: '#F3F4F6', color: '#6B7280' },
  flagged: { label: 'Flagged', bg: '#FEF3C7', color: '#D97706' },
  contacted: { label: 'Contacted', bg: '#DBEAFE', color: '#2563EB' },
  new_case_created: { label: 'Case Created', bg: '#D1FAE5', color: '#059669' },
};

const fmtCurrency = (v) => (v ? '£' + Number(v).toLocaleString('en-GB') : '—');

function rowBorderColor(days) {
  if (days === null) return 'transparent';
  if (days < 0) return '#EF4444';
  if (days <= 30) return '#EF4444';
  if (days <= 90) return '#F59E0B';
  if (days <= 180) return '#0E9F6E';
  return 'transparent';
}

function DaysCell({ days }) {
  if (days === null) return <span className="text-[#6B7280]">—</span>;
  if (days === 0) return <span style={{ color: '#EF4444', fontWeight: 700 }}>Today</span>;
  if (days < 0) return <span style={{ color: '#EF4444' }}>Expired {Math.abs(days)} days ago</span>;
  const color = days <= 90 ? '#EF4444' : days <= 180 ? '#F59E0B' : '#0E9F6E';
  if (days > 180) return <span style={{ color: '#6B7280' }}>{days} days</span>;
  return <span style={{ color, fontWeight: 600 }}>{days} days</span>;
}

function StatusBadge({ status }) {
  const cfg = STATUS_LABELS[status] || STATUS_LABELS.none;
  return (
    <span style={{
      background: cfg.bg, color: cfg.color, padding: '2px 10px',
      borderRadius: '9999px', fontSize: '12px', fontWeight: 600, whiteSpace: 'nowrap',
    }}>
      {cfg.label}
    </span>
  );
}

export default function Retention() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [cases, setCases] = useState([]);
  const [summary, setSummary] = useState({ total_monitored: 0, expiring_90_days: 0, expiring_180_days: 0, already_expired: 0 });
  const [loading, setLoading] = useState(true);
  const [lenders, setLenders] = useState([]);

  // Filters
  const [windowFilter, setWindowFilter] = useState(searchParams.get('window') ? parseInt(searchParams.get('window')) : '');
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');

  // Create case modal
  const [modal, setModal] = useState(null); // { originalCase } or null
  const [modalForm, setModalForm] = useState({});
  const [modalLoading, setModalLoading] = useState(false);

  const fetchCases = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (windowFilter !== '' && windowFilter !== 'all') params.set('window', windowFilter);
      if (statusFilter) params.set('status', statusFilter);
      const { data } = await axios.get(`${API}/retention/cases?${params}`, { withCredentials: true });
      setCases(data.data.cases);
      setSummary(data.data.summary);
    } catch {
      toast.error('Failed to load retention pipeline');
    } finally {
      setLoading(false);
    }
  }, [windowFilter, statusFilter]);

  useEffect(() => { fetchCases(); }, [fetchCases]);

  useEffect(() => {
    axios.get(`${API}/lenders?page=1&limit=1000`, { withCredentials: true })
      .then(({ data }) => setLenders(data.data || []))
      .catch(() => {});
  }, []);

  const handleMarkContacted = async (caseId) => {
    // Optimistic update
    setCases(prev => prev.map(c => c.id === caseId ? { ...c, retention_status: 'contacted' } : c));
    try {
      await axios.patch(`${API}/retention/cases/${caseId}/status`, { retention_status: 'contacted' }, { withCredentials: true });
    } catch {
      toast.error('Failed to update status');
      fetchCases();
    }
  };

  const openCreateModal = (retCase) => {
    setModalForm({
      client_id: retCase.client_id || '',
      client_name: retCase.client_name,
      mortgage_type: 'remortgage',
      loan_amount: retCase.loan_amount || '',
      lender_id: retCase.lender_id || '',
      term_years: retCase.term_years || '',
      stage: 'new_enquiry',
      rate_expiry_date: '',
    });
    setModal(retCase);
  };

  const handleCreateCase = async () => {
    if (!modal) return;
    setModalLoading(true);
    try {
      // First we need client_id and lender_id from the original case
      const origCase = await axios.get(`${API}/cases/${modal.id}`, { withCredentials: true });
      const orig = origCase.data.data;

      const payload = {
        client_id: orig.client_id,
        mortgage_type: modalForm.mortgage_type,
        loan_amount: modalForm.loan_amount ? parseFloat(modalForm.loan_amount) : undefined,
        lender_id: modalForm.lender_id || undefined,
        term_years: modalForm.term_years ? parseInt(modalForm.term_years) : undefined,
        stage: 'new_enquiry',
      };
      const { data } = await axios.post(`${API}/cases`, payload, { withCredentials: true });
      const newCaseId = data.data.id;

      // Update original case retention_status
      await axios.patch(`${API}/retention/cases/${modal.id}/status`, { retention_status: 'new_case_created' }, { withCredentials: true });

      toast.success('New case created successfully');
      setModal(null);
      navigate(`/cases/${newCaseId}`);
    } catch {
      toast.error('Failed to create case');
    } finally {
      setModalLoading(false);
    }
  };

  // Client-side search filter
  const filtered = cases.filter(c => {
    if (!search) return true;
    const q = search.toLowerCase();
    return c.client_name.toLowerCase().includes(q) || c.lender_name.toLowerCase().includes(q);
  });

  // Special window filter for "already expired" (-1)
  const displayCases = windowFilter === -1
    ? filtered.filter(c => c.days_until_expiry < 0)
    : filtered;

  const clearFilters = () => { setWindowFilter(''); setStatusFilter(''); setSearch(''); };

  return (
    <div className="p-8" data-testid="retention-page">
      {/* Heading */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[#0A2342]" data-testid="retention-heading">Retention Pipeline</h1>
        <p className="text-[#6B7280] mt-1">Track clients approaching rate expiry and act before their fixed rate ends.</p>
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Monitoring', value: summary.total_monitored, color: '#0A2342' },
          { label: 'Expiring in 90 Days', value: summary.expiring_90_days, color: '#EF4444' },
          { label: 'Expiring 90–180 Days', value: summary.expiring_180_days, color: '#F59E0B' },
          { label: 'Already Expired', value: summary.already_expired, color: '#9CA3AF' },
        ].map(stat => (
          <div key={stat.label} className="bg-white rounded-lg border border-[#E5E7EB] p-4" data-testid={`stat-${stat.label.toLowerCase().replace(/\s+/g,'-')}`}>
            <div className="text-sm text-[#6B7280]">{stat.label}</div>
            <div className="text-3xl font-bold mt-1" style={{ color: stat.color }}>{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <select
          value={windowFilter}
          onChange={e => setWindowFilter(e.target.value === '' ? '' : parseInt(e.target.value))}
          className="border border-[#E5E7EB] rounded-md px-3 py-2 text-sm text-[#111827] focus:outline-none focus:ring-1 focus:ring-[#0E9F6E]"
          data-testid="filter-window"
        >
          <option value="">All Expiry Windows</option>
          <option value="30">Next 30 days</option>
          <option value="90">Next 90 days</option>
          <option value="180">Next 180 days</option>
          <option value="-1">Already Expired</option>
        </select>
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="border border-[#E5E7EB] rounded-md px-3 py-2 text-sm text-[#111827] focus:outline-none focus:ring-1 focus:ring-[#0E9F6E]"
          data-testid="filter-status"
        >
          <option value="">All Statuses</option>
          <option value="none">Not Contacted</option>
          <option value="contacted">Contacted</option>
          <option value="new_case_created">New Case Created</option>
        </select>
        <input
          type="text"
          placeholder="Search client or lender…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="border border-[#E5E7EB] rounded-md px-3 py-2 text-sm text-[#111827] focus:outline-none focus:ring-1 focus:ring-[#0E9F6E] flex-1 max-w-xs"
          data-testid="filter-search"
        />
        {(windowFilter !== '' || statusFilter || search) && (
          <button onClick={clearFilters} className="text-sm text-[#0E9F6E] hover:underline" data-testid="clear-filters">
            Clear Filters
          </button>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <div className="space-y-2" data-testid="retention-skeleton">
          {[1,2,3].map(i => (
            <div key={i} className="h-14 bg-[#F3F4F6] rounded animate-pulse" />
          ))}
        </div>
      ) : displayCases.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center" data-testid="retention-empty">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" className="mb-4">
            <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" fill="#0E9F6E" opacity="0.2" stroke="#0E9F6E" strokeWidth="1.5"/>
            <path d="M9 12l2 2 4-4" stroke="#0E9F6E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <p className="text-[#0A2342] font-semibold text-lg">No cases to monitor yet</p>
          <p className="text-[#6B7280] text-sm mt-1 max-w-xs">Cases will appear here once they reach Completion stage and have a Rate Expiry Date set.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-[#E5E7EB] overflow-hidden">
          <table className="w-full text-sm" data-testid="retention-table">
            <thead>
              <tr className="border-b border-[#E5E7EB] bg-[#F9FAFB]">
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Client Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Lender</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Rate</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Expiry Date</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Days Until Expiry</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody>
              {displayCases.map(c => {
                const borderColor = rowBorderColor(c.days_until_expiry);
                const alreadyActed = c.retention_status === 'contacted' || c.retention_status === 'new_case_created';
                return (
                  <tr
                    key={c.id}
                    className="border-b border-[#E5E7EB] hover:bg-[#F9FAFB] transition-colors"
                    style={{ borderLeft: borderColor !== 'transparent' ? `4px solid ${borderColor}` : '4px solid transparent' }}
                    data-testid={`retention-row-${c.id}`}
                  >
                    <td className="px-4 py-3 font-medium text-[#111827]">{c.client_name}</td>
                    <td className="px-4 py-3 text-[#374151]">{c.lender_name}</td>
                    <td className="px-4 py-3 text-[#374151]">
                      {c.rate_percent ? `${c.rate_percent}% ${c.rate_type || ''}`.trim() : '—'}
                    </td>
                    <td className="px-4 py-3 text-[#374151]">{c.rate_expiry_date || '—'}</td>
                    <td className="px-4 py-3"><DaysCell days={c.days_until_expiry} /></td>
                    <td className="px-4 py-3"><StatusBadge status={c.retention_status} /></td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2 flex-wrap">
                        <button
                          onClick={() => !alreadyActed && handleMarkContacted(c.id)}
                          disabled={alreadyActed}
                          className="text-xs px-2 py-1 rounded border font-medium transition-colors"
                          style={{
                            borderColor: alreadyActed ? '#E5E7EB' : '#0E9F6E',
                            color: alreadyActed ? '#9CA3AF' : '#0E9F6E',
                            cursor: alreadyActed ? 'not-allowed' : 'pointer',
                            background: 'white',
                          }}
                          data-testid={`mark-contacted-${c.id}`}
                        >
                          Mark Contacted
                        </button>
                        <button
                          onClick={() => openCreateModal(c)}
                          className="text-xs px-2 py-1 rounded border border-[#0A2342] text-[#0A2342] font-medium hover:bg-[#0A2342] hover:text-white transition-colors"
                          data-testid={`create-case-${c.id}`}
                        >
                          Create Case
                        </button>
                        <button
                          onClick={() => navigate(`/cases/${c.id}`)}
                          className="text-xs px-2 py-1 rounded border border-[#E5E7EB] text-[#6B7280] font-medium hover:bg-[#F3F4F6] transition-colors"
                          data-testid={`view-case-${c.id}`}
                        >
                          View Case
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Case Modal */}
      {modal && (
        <div
          className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50"
          onClick={(e) => e.target === e.currentTarget && setModal(null)}
          data-testid="create-case-modal"
        >
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="px-6 py-4 border-b border-[#E5E7EB]">
              <h2 className="text-base font-bold text-[#0A2342]">New Case — {modal.client_name}</h2>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div>
                <label className="text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Client</label>
                <div className="mt-1 px-3 py-2 bg-[#F9FAFB] rounded border border-[#E5E7EB] text-sm text-[#374151]">{modal.client_name}</div>
              </div>
              <div>
                <label className="text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Mortgage Type</label>
                <select
                  value={modalForm.mortgage_type}
                  onChange={e => setModalForm(f => ({ ...f, mortgage_type: e.target.value }))}
                  className="mt-1 w-full border border-[#E5E7EB] rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#0E9F6E]"
                  data-testid="modal-mortgage-type"
                >
                  {MORTGAGE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Loan Amount (£)</label>
                <input
                  type="number"
                  value={modalForm.loan_amount}
                  onChange={e => setModalForm(f => ({ ...f, loan_amount: e.target.value }))}
                  className="mt-1 w-full border border-[#E5E7EB] rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#0E9F6E]"
                  data-testid="modal-loan-amount"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Lender</label>
                <select
                  value={modalForm.lender_id}
                  onChange={e => setModalForm(f => ({ ...f, lender_id: e.target.value }))}
                  className="mt-1 w-full border border-[#E5E7EB] rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#0E9F6E]"
                  data-testid="modal-lender"
                >
                  <option value="">Select Lender</option>
                  {lenders.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Term (Years)</label>
                <input
                  type="number"
                  value={modalForm.term_years}
                  onChange={e => setModalForm(f => ({ ...f, term_years: e.target.value }))}
                  className="mt-1 w-full border border-[#E5E7EB] rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#0E9F6E]"
                  data-testid="modal-term-years"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-[#E5E7EB] flex gap-3 justify-end">
              <button
                onClick={() => setModal(null)}
                className="px-4 py-2 text-sm text-[#6B7280] border border-[#E5E7EB] rounded hover:bg-[#F3F4F6] transition-colors"
                data-testid="modal-cancel"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateCase}
                disabled={modalLoading}
                className="px-4 py-2 text-sm text-white rounded font-medium transition-colors"
                style={{ background: modalLoading ? '#9CA3AF' : '#0E9F6E', cursor: modalLoading ? 'not-allowed' : 'pointer' }}
                data-testid="modal-create-case"
              >
                {modalLoading ? 'Creating…' : 'Create Case'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
