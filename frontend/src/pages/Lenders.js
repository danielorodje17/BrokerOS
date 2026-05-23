import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Checkbox } from '../components/ui/checkbox';
import { Skeleton } from '../components/ui/skeleton';
import { Textarea } from '../components/ui/textarea';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const formatCurrency = (value) => {
  if (!value) return '-';
  return '£' + value.toLocaleString('en-GB');
};

export function Lenders() {
  const [lenders, setLenders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingLender, setEditingLender] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    bdm_name: '',
    bdm_email: '',
    bdm_phone: '',
    proc_fee_purchase: '',
    proc_fee_remortgage: '',
    proc_fee_btl: '',
    min_loan: '',
    max_loan: '',
    max_ltv: '',
    min_income: '',
    accepts_self_employed: false,
    accepts_contractors: false,
    accepts_adverse: false,
    avg_processing_days: '',
    broker_success_rate: '',
    notes: ''
  });
  const [saving, setSaving] = useState(false);

  // ---- Filter panel state ----
  const [filterOpen, setFilterOpen] = useState(false);
  const [filterForm, setFilterForm] = useState({
    loanAmount: '',
    propertyValue: '',
    employmentType: 'All',
    creditProfile: 'All',
  });
  const [filteredLenders, setFilteredLenders] = useState(null); // null = show normal paginated view
  const [matchResult, setMatchResult] = useState(null); // { count, noFilters }

  const computedLTV = useMemo(() => {
    const loan = parseFloat(filterForm.loanAmount);
    const prop = parseFloat(filterForm.propertyValue);
    if (!loan || !prop || prop === 0) return null;
    return ((loan / prop) * 100).toFixed(1);
  }, [filterForm.loanAmount, filterForm.propertyValue]);

  useEffect(() => {
    fetchLenders();
  }, [page, search]);

  const fetchLenders = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, limit: 20 });
      if (search) params.append('search', search);
      const { data } = await axios.get(`${API}/lenders?${params}`, { withCredentials: true });
      setLenders(data.lenders);
      setTotal(data.total);
    } catch (error) {
      toast.error('Failed to load lenders');
    } finally {
      setLoading(false);
    }
  };

  const openDialog = (lender = null) => {
    if (lender) {
      setEditingLender(lender);
      setFormData({
        name: lender.name || '',
        bdm_name: lender.bdm_name || '',
        bdm_email: lender.bdm_email || '',
        bdm_phone: lender.bdm_phone || '',
        proc_fee_purchase: lender.proc_fee_purchase || '',
        proc_fee_remortgage: lender.proc_fee_remortgage || '',
        proc_fee_btl: lender.proc_fee_btl || '',
        min_loan: lender.min_loan || '',
        max_loan: lender.max_loan || '',
        max_ltv: lender.max_ltv || '',
        min_income: lender.min_income || '',
        accepts_self_employed: lender.accepts_self_employed || false,
        accepts_contractors: lender.accepts_contractors || false,
        accepts_adverse: lender.accepts_adverse || false,
        avg_processing_days: lender.avg_processing_days || '',
        broker_success_rate: lender.broker_success_rate || '',
        notes: lender.notes || ''
      });
    } else {
      setEditingLender(null);
      setFormData({
        name: '',
        bdm_name: '',
        bdm_email: '',
        bdm_phone: '',
        proc_fee_purchase: '',
        proc_fee_remortgage: '',
        proc_fee_btl: '',
        min_loan: '',
        max_loan: '',
        max_ltv: '',
        min_income: '',
        accepts_self_employed: false,
        accepts_contractors: false,
        accepts_adverse: false,
        avg_processing_days: '',
        broker_success_rate: '',
        notes: ''
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);

    const payload = {
      ...formData,
      proc_fee_purchase: formData.proc_fee_purchase ? parseFloat(formData.proc_fee_purchase) : null,
      proc_fee_remortgage: formData.proc_fee_remortgage ? parseFloat(formData.proc_fee_remortgage) : null,
      proc_fee_btl: formData.proc_fee_btl ? parseFloat(formData.proc_fee_btl) : null,
      min_loan: formData.min_loan ? parseFloat(formData.min_loan) : null,
      max_loan: formData.max_loan ? parseFloat(formData.max_loan) : null,
      max_ltv: formData.max_ltv ? parseFloat(formData.max_ltv) : null,
      min_income: formData.min_income ? parseFloat(formData.min_income) : null,
      avg_processing_days: formData.avg_processing_days ? parseInt(formData.avg_processing_days) : null,
      broker_success_rate: formData.broker_success_rate ? parseFloat(formData.broker_success_rate) : null
    };

    try {
      if (editingLender) {
        await axios.put(`${API}/lenders/${editingLender.id}`, payload, { withCredentials: true });
        toast.success('Lender updated');
      } else {
        await axios.post(`${API}/lenders`, payload, { withCredentials: true });
        toast.success('Lender added');
      }
      setDialogOpen(false);
      fetchLenders();
    } catch (error) {
      toast.error(editingLender ? 'Failed to update lender' : 'Failed to add lender');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (lenderId) => {
    if (!window.confirm('Are you sure you want to delete this lender?')) return;
    try {
      await axios.delete(`${API}/lenders/${lenderId}`, { withCredentials: true });
      toast.success('Lender deleted');
      fetchLenders();
    } catch (error) {
      toast.error('Failed to delete lender');
    }
  };

  const handleMatchLenders = async () => {
    setFilterOpen(false);
    try {
      const { data } = await axios.get(`${API}/lenders?page=1&limit=1000`, { withCredentials: true });
      const allLenders = data.lenders;

      const loan = parseFloat(filterForm.loanAmount);
      const prop = parseFloat(filterForm.propertyValue);
      const ltv = loan && prop && prop > 0 ? (loan / prop) * 100 : null;

      const noFilters =
        !filterForm.loanAmount &&
        !filterForm.propertyValue &&
        filterForm.employmentType === 'All' &&
        filterForm.creditProfile === 'All';

      const matched = allLenders.filter((l) => {
        if (loan) {
          if (l.min_loan && loan < l.min_loan) return false;
          if (l.max_loan && loan > l.max_loan) return false;
        }
        if (ltv !== null && l.max_ltv && ltv > l.max_ltv) return false;
        if (filterForm.employmentType === 'Self-Employed' && !l.accepts_self_employed) return false;
        if (filterForm.employmentType === 'Contractor' && !l.accepts_contractors) return false;
        if (filterForm.creditProfile === 'Adverse' && !l.accepts_adverse) return false;
        return true;
      });

      matched.sort((a, b) => (b.proc_fee_purchase || 0) - (a.proc_fee_purchase || 0));

      setFilteredLenders(matched);
      setMatchResult({ count: matched.length, noFilters });
    } catch {
      toast.error('Failed to load lenders for matching');
    }
  };

  const handleClearClose = () => {
    setFilterForm({ loanAmount: '', propertyValue: '', employmentType: 'All', creditProfile: 'All' });
    setFilteredLenders(null);
    setMatchResult(null);
    setFilterOpen(false);
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div data-testid="lenders-page">
      <div className="page-header">
        <h1>Lender Panel</h1>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => setFilterOpen(true)}
            className="bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
            data-testid="find-lender-btn"
          >
            Find a Lender
          </Button>
          <Button
            onClick={() => openDialog()}
            className="bg-[#0A2342] hover:bg-[#0d1f38] text-white"
            data-testid="add-lender-btn"
          >
            Add Lender
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="search-bar">
        <Input
          type="text"
          placeholder="Search lenders..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="form-input search-input"
          data-testid="search-input"
        />
      </div>

      {/* Match result pill */}
      {matchResult !== null && (
        <div className="flex items-center gap-3 mb-3" data-testid="match-result-pill">
          <span
            className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
              matchResult.noFilters
                ? 'bg-[#F3F4F6] text-[#6B7280]'
                : matchResult.count > 0
                ? 'bg-[#0E9F6E]/10 text-[#0E9F6E]'
                : 'bg-[#FEE2E2] text-[#DC2626]'
            }`}
            data-testid="match-result-count"
          >
            {matchResult.noFilters
              ? `${matchResult.count} lenders — no filters applied`
              : matchResult.count > 0
              ? `${matchResult.count} lenders matched your criteria`
              : 'No lenders matched your criteria'}
          </span>
          <button
            onClick={() => { setFilteredLenders(null); setMatchResult(null); }}
            className="text-xs text-[#6B7280] hover:underline"
            data-testid="clear-filter-link"
          >
            Clear filter
          </button>
        </div>
      )}

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="table-header">
              <th className="text-left px-4 py-3">Lender</th>
              <th className="text-left px-4 py-3">BDM Contact</th>
              <th className="text-left px-4 py-3">Proc Fee</th>
              <th className="text-left px-4 py-3">Max LTV</th>
              <th className="text-left px-4 py-3">Loan Range</th>
              <th className="text-left px-4 py-3">Accepts</th>
              <th className="text-right px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="table-row">
                  <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-40" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-16" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-12" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20 ml-auto" /></td>
                </tr>
              ))
            ) : (filteredLenders !== null ? filteredLenders : lenders).length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="empty-state">
                    <h3>No lenders yet</h3>
                    <p>Add lenders to your panel</p>
                    <Button
                      onClick={() => openDialog()}
                      className="bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
                      data-testid="empty-add-lender-btn"
                    >
                      Add Lender
                    </Button>
                  </div>
                </td>
              </tr>
            ) : (
              (filteredLenders !== null ? filteredLenders : lenders).map((lender) => (
                <tr key={lender.id} className="table-row" data-testid={`lender-row-${lender.id}`}>
                  <td className="px-4 py-3 font-medium text-[#111827]">{lender.name}</td>
                  <td className="px-4 py-3">
                    <div className="text-[#111827]">{lender.bdm_name || '-'}</div>
                    <div className="text-xs text-[#6B7280]">{lender.bdm_email}</div>
                  </td>
                  <td className="px-4 py-3 text-[#111827]">
                    {lender.proc_fee_purchase ? `${lender.proc_fee_purchase}%` : '-'}
                  </td>
                  <td className="px-4 py-3 text-[#111827]">
                    {lender.max_ltv ? `${lender.max_ltv}%` : '-'}
                  </td>
                  <td className="px-4 py-3 text-[#6B7280] text-sm">
                    {lender.min_loan || lender.max_loan
                      ? `${formatCurrency(lender.min_loan)} - ${formatCurrency(lender.max_loan)}`
                      : '-'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 flex-wrap">
                      {lender.accepts_self_employed && (
                        <span className="badge badge-blue text-xs">SE</span>
                      )}
                      {lender.accepts_contractors && (
                        <span className="badge badge-blue text-xs">Con</span>
                      )}
                      {lender.accepts_adverse && (
                        <span className="badge badge-amber text-xs">Adv</span>
                      )}
                      {!lender.accepts_self_employed && !lender.accepts_contractors && !lender.accepts_adverse && (
                        <span className="text-[#6B7280]">-</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => openDialog(lender)}
                      className="text-[#0E9F6E] hover:underline text-sm mr-3"
                      data-testid={`edit-lender-${lender.id}`}
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(lender.id)}
                      className="text-[#EF4444] hover:underline text-sm"
                      data-testid={`delete-lender-${lender.id}`}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination — hidden when filter is active */}
      {filteredLenders === null && totalPages > 1 && (
        <div className="flex justify-between items-center mt-4">
          <span className="text-sm text-[#6B7280]">
            Showing {((page - 1) * 20) + 1} to {Math.min(page * 20, total)} of {total} lenders
          </span>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="border-[#E5E7EB]">
              Previous
            </Button>
            <Button variant="outline" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="border-[#E5E7EB]">
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Filter Panel Backdrop */}
      {filterOpen && (
        <div
          className="fixed inset-0 z-40"
          style={{ background: 'rgba(0,0,0,0.2)' }}
          onClick={() => setFilterOpen(false)}
          data-testid="filter-backdrop"
        />
      )}

      {/* Filter Panel — slides in from the right */}
      <div
        className="fixed right-0 top-0 h-full bg-white flex flex-col z-50"
        style={{
          width: '320px',
          borderLeft: '1px solid #D1D5DB',
          transform: filterOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.3s ease',
        }}
        data-testid="filter-panel"
      >
        {/* Panel Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#E5E7EB]">
          <h2 className="text-[#111827] font-semibold text-sm">Find a Lender</h2>
          <button
            onClick={() => setFilterOpen(false)}
            className="text-[#6B7280] hover:text-[#111827] text-xl leading-none"
            data-testid="filter-panel-close"
            aria-label="Close filter panel"
          >
            ×
          </button>
        </div>

        {/* Panel Form */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          <div>
            <label className="form-label">Loan Amount (£)</label>
            <Input
              type="number"
              min="0"
              step="1"
              value={filterForm.loanAmount}
              onChange={(e) => setFilterForm((f) => ({ ...f, loanAmount: e.target.value }))}
              placeholder="e.g. 250000"
              className="form-input"
              data-testid="filter-loan-amount"
            />
          </div>

          <div>
            <label className="form-label">Property Value (£)</label>
            <Input
              type="number"
              min="0"
              step="1"
              value={filterForm.propertyValue}
              onChange={(e) => setFilterForm((f) => ({ ...f, propertyValue: e.target.value }))}
              placeholder="e.g. 320000"
              className="form-input"
              data-testid="filter-property-value"
            />
          </div>

          {/* Real-time LTV */}
          <p className="text-sm font-medium text-[#0E9F6E]" data-testid="filter-ltv-display">
            {computedLTV ? `LTV: ${computedLTV}%` : 'LTV: —'}
          </p>

          <div>
            <label className="form-label">Employment Type</label>
            <select
              value={filterForm.employmentType}
              onChange={(e) => setFilterForm((f) => ({ ...f, employmentType: e.target.value }))}
              className="form-input w-full"
              data-testid="filter-employment-type"
            >
              <option value="All">All</option>
              <option value="Employed">Employed</option>
              <option value="Self-Employed">Self-Employed</option>
              <option value="Contractor">Contractor</option>
              <option value="Retired">Retired</option>
            </select>
          </div>

          <div>
            <label className="form-label">Credit Profile</label>
            <select
              value={filterForm.creditProfile}
              onChange={(e) => setFilterForm((f) => ({ ...f, creditProfile: e.target.value }))}
              className="form-input w-full"
              data-testid="filter-credit-profile"
            >
              <option value="All">All</option>
              <option value="Clean">Clean</option>
              <option value="Minor Issues">Minor Issues</option>
              <option value="Adverse">Adverse</option>
            </select>
          </div>
        </div>

        {/* Panel Footer */}
        <div className="p-4 border-t border-[#E5E7EB] space-y-3">
          <Button
            onClick={handleMatchLenders}
            className="w-full bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
            data-testid="match-lenders-btn"
          >
            Match Lenders
          </Button>
          <div className="text-center">
            <button
              onClick={handleClearClose}
              className="text-sm text-[#6B7280] hover:text-[#111827] hover:underline"
              data-testid="clear-close-btn"
            >
              Clear &amp; Close
            </button>
          </div>
        </div>
      </div>

      {/* Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingLender ? 'Edit Lender' : 'Add Lender'}</DialogTitle>
            <DialogDescription className="sr-only">
              {editingLender ? 'Edit lender details' : 'Add a new lender to your panel'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-5 mt-4">
            <div>
              <label className="form-label">Lender name <span className="text-[#0E9F6E]">*</span></label>
              <Input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                placeholder="e.g. Nationwide"
                className="form-input"
                data-testid="lender-name-input"
              />
            </div>

            <h3 className="text-sm font-semibold text-[#111827] pt-2">BDM Contact</h3>
            <div className="form-grid">
              <div>
                <label className="form-label">BDM name</label>
                <Input
                  type="text"
                  value={formData.bdm_name}
                  onChange={(e) => setFormData({ ...formData, bdm_name: e.target.value })}
                  className="form-input"
                  data-testid="bdm-name-input"
                />
              </div>
              <div>
                <label className="form-label">BDM email</label>
                <Input
                  type="email"
                  value={formData.bdm_email}
                  onChange={(e) => setFormData({ ...formData, bdm_email: e.target.value })}
                  className="form-input"
                  data-testid="bdm-email-input"
                />
              </div>
            </div>
            <div>
              <label className="form-label">BDM phone</label>
              <Input
                type="tel"
                value={formData.bdm_phone}
                onChange={(e) => setFormData({ ...formData, bdm_phone: e.target.value })}
                className="form-input max-w-xs"
                data-testid="bdm-phone-input"
              />
            </div>

            <h3 className="text-sm font-semibold text-[#111827] pt-2">Proc Fees (%)</h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="form-label">Purchase</label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.proc_fee_purchase}
                  onChange={(e) => setFormData({ ...formData, proc_fee_purchase: e.target.value })}
                  placeholder="0.35"
                  className="form-input"
                  data-testid="proc-fee-purchase-input"
                />
              </div>
              <div>
                <label className="form-label">Remortgage</label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.proc_fee_remortgage}
                  onChange={(e) => setFormData({ ...formData, proc_fee_remortgage: e.target.value })}
                  placeholder="0.35"
                  className="form-input"
                  data-testid="proc-fee-remortgage-input"
                />
              </div>
              <div>
                <label className="form-label">BTL</label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.proc_fee_btl}
                  onChange={(e) => setFormData({ ...formData, proc_fee_btl: e.target.value })}
                  placeholder="0.40"
                  className="form-input"
                  data-testid="proc-fee-btl-input"
                />
              </div>
            </div>

            <h3 className="text-sm font-semibold text-[#111827] pt-2">Lending Criteria</h3>
            <div className="form-grid">
              <div>
                <label className="form-label">Min loan (£)</label>
                <Input
                  type="number"
                  value={formData.min_loan}
                  onChange={(e) => setFormData({ ...formData, min_loan: e.target.value })}
                  placeholder="25000"
                  className="form-input"
                  data-testid="min-loan-input"
                />
              </div>
              <div>
                <label className="form-label">Max loan (£)</label>
                <Input
                  type="number"
                  value={formData.max_loan}
                  onChange={(e) => setFormData({ ...formData, max_loan: e.target.value })}
                  placeholder="2000000"
                  className="form-input"
                  data-testid="max-loan-input"
                />
              </div>
            </div>
            <div className="form-grid">
              <div>
                <label className="form-label">Max LTV (%)</label>
                <Input
                  type="number"
                  value={formData.max_ltv}
                  onChange={(e) => setFormData({ ...formData, max_ltv: e.target.value })}
                  placeholder="95"
                  className="form-input"
                  data-testid="max-ltv-input"
                />
              </div>
              <div>
                <label className="form-label">Min income (£)</label>
                <Input
                  type="number"
                  value={formData.min_income}
                  onChange={(e) => setFormData({ ...formData, min_income: e.target.value })}
                  placeholder="20000"
                  className="form-input"
                  data-testid="min-income-input"
                />
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <label className="flex items-center gap-3">
                <Checkbox
                  checked={formData.accepts_self_employed}
                  onCheckedChange={(checked) => setFormData({ ...formData, accepts_self_employed: checked })}
                  data-testid="accepts-se-checkbox"
                />
                <span className="text-sm text-[#111827]">Accepts self-employed</span>
              </label>
              <label className="flex items-center gap-3">
                <Checkbox
                  checked={formData.accepts_contractors}
                  onCheckedChange={(checked) => setFormData({ ...formData, accepts_contractors: checked })}
                  data-testid="accepts-contractors-checkbox"
                />
                <span className="text-sm text-[#111827]">Accepts contractors</span>
              </label>
              <label className="flex items-center gap-3">
                <Checkbox
                  checked={formData.accepts_adverse}
                  onCheckedChange={(checked) => setFormData({ ...formData, accepts_adverse: checked })}
                  data-testid="accepts-adverse-checkbox"
                />
                <span className="text-sm text-[#111827]">Accepts adverse credit</span>
              </label>
            </div>

            <h3 className="text-sm font-semibold text-[#111827] pt-2">Performance</h3>
            <div className="form-grid">
              <div>
                <label className="form-label">Avg processing days</label>
                <Input
                  type="number"
                  value={formData.avg_processing_days}
                  onChange={(e) => setFormData({ ...formData, avg_processing_days: e.target.value })}
                  placeholder="21"
                  className="form-input"
                  data-testid="avg-days-input"
                />
              </div>
              <div>
                <label className="form-label">Your success rate (%)</label>
                <Input
                  type="number"
                  value={formData.broker_success_rate}
                  onChange={(e) => setFormData({ ...formData, broker_success_rate: e.target.value })}
                  placeholder="85"
                  className="form-input"
                  data-testid="success-rate-input"
                />
              </div>
            </div>

            <div>
              <label className="form-label">Notes</label>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Add any notes about this lender..."
                className="form-input min-h-[80px]"
                data-testid="lender-notes-input"
              />
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} className="border-[#E5E7EB]">
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={saving}
                className="bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
                data-testid="save-lender-btn"
              >
                {saving ? 'Saving...' : editingLender ? 'Update Lender' : 'Add Lender'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
