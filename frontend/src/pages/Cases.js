import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Skeleton } from '../components/ui/skeleton';
import { Textarea } from '../components/ui/textarea';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const mortgageTypes = [
  { value: 'residential', label: 'Residential' },
  { value: 'btl', label: 'Buy to Let' },
  { value: 'remortgage', label: 'Remortgage' },
  { value: 'product_transfer', label: 'Product Transfer' },
  { value: 'bridging', label: 'Bridging' }
];

const stages = [
  { value: 'new_enquiry', label: 'New Enquiry', badge: 'badge-grey' },
  { value: 'fact_find', label: 'Fact Find', badge: 'badge-grey' },
  { value: 'aip_submitted', label: 'AIP Submitted', badge: 'badge-amber' },
  { value: 'aip_received', label: 'AIP Received', badge: 'badge-amber' },
  { value: 'full_application', label: 'Full Application', badge: 'badge-blue' },
  { value: 'valuation', label: 'Valuation', badge: 'badge-blue' },
  { value: 'offer', label: 'Mortgage Offer', badge: 'badge-teal' },
  { value: 'exchange', label: 'Exchange', badge: 'badge-teal' },
  { value: 'completion', label: 'Completion', badge: 'badge-green' },
  { value: 'on_hold', label: 'On Hold', badge: 'badge-orange' },
  { value: 'declined', label: 'Declined', badge: 'badge-red' }
];

const rateTypes = [
  { value: 'fixed', label: 'Fixed' },
  { value: 'variable', label: 'Variable' },
  { value: 'tracker', label: 'Tracker' }
];

const formatCurrency = (value) => {
  if (!value) return '-';
  return '£' + value.toLocaleString('en-GB');
};

export function Cases() {
  const [cases, setCases] = useState([]);
  const [clients, setClients] = useState([]);
  const [lenders, setLenders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [stageFilter, setStageFilter] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingCase, setEditingCase] = useState(null);
  const [formData, setFormData] = useState({
    client_id: '',
    mortgage_type: 'residential',
    stage: 'new_enquiry',
    loan_amount: '',
    property_value: '',
    term_years: '',
    lender_id: '',
    rate_type: '',
    rate_percent: '',
    rate_expiry_date: '',
    expected_completion_date: '',
    notes: ''
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchData();
  }, [page, search, stageFilter]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, limit: 20 });
      if (search) params.append('search', search);
      if (stageFilter) params.append('stage', stageFilter);

      const [casesRes, clientsRes, lendersRes] = await Promise.all([
        axios.get(`${API}/cases?${params}`, { withCredentials: true }),
        axios.get(`${API}/clients?limit=100`, { withCredentials: true }),
        axios.get(`${API}/lenders?limit=100`, { withCredentials: true })
      ]);

      setCases(casesRes.data.cases);
      setTotal(casesRes.data.total);
      setClients(clientsRes.data.clients);
      setLenders(lendersRes.data.lenders);
    } catch (error) {
      toast.error('Failed to load cases');
    } finally {
      setLoading(false);
    }
  };

  const openDialog = (caseData = null) => {
    if (caseData) {
      setEditingCase(caseData);
      setFormData({
        client_id: caseData.client_id || '',
        mortgage_type: caseData.mortgage_type || 'residential',
        stage: caseData.stage || 'new_enquiry',
        loan_amount: caseData.loan_amount || '',
        property_value: caseData.property_value || '',
        term_years: caseData.term_years || '',
        lender_id: caseData.lender_id || '',
        rate_type: caseData.rate_type || '',
        rate_percent: caseData.rate_percent || '',
        rate_expiry_date: caseData.rate_expiry_date || '',
        expected_completion_date: caseData.expected_completion_date || '',
        notes: caseData.notes || ''
      });
    } else {
      setEditingCase(null);
      setFormData({
        client_id: '',
        mortgage_type: 'residential',
        stage: 'new_enquiry',
        loan_amount: '',
        property_value: '',
        term_years: '',
        lender_id: '',
        rate_type: '',
        rate_percent: '',
        rate_expiry_date: '',
        expected_completion_date: '',
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
      loan_amount: formData.loan_amount ? parseFloat(formData.loan_amount) : null,
      property_value: formData.property_value ? parseFloat(formData.property_value) : null,
      term_years: formData.term_years ? parseInt(formData.term_years) : null,
      rate_percent: formData.rate_percent ? parseFloat(formData.rate_percent) : null,
      lender_id: formData.lender_id || null
    };

    try {
      if (editingCase) {
        await axios.put(`${API}/cases/${editingCase.id}`, payload, { withCredentials: true });
        toast.success('Case updated');
      } else {
        await axios.post(`${API}/cases`, payload, { withCredentials: true });
        toast.success('Case created');
      }
      setDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(editingCase ? 'Failed to update case' : 'Failed to create case');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (caseId) => {
    if (!window.confirm('Are you sure you want to delete this case?')) return;
    try {
      await axios.delete(`${API}/cases/${caseId}`, { withCredentials: true });
      toast.success('Case deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete case');
    }
  };

  const getStageInfo = (stage) => stages.find(s => s.value === stage) || { label: stage, badge: 'badge-grey' };

  const totalPages = Math.ceil(total / 20);

  return (
    <div data-testid="cases-page">
      <div className="page-header">
        <h1>Cases</h1>
        <Button
          onClick={() => openDialog()}
          className="bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
          data-testid="add-case-btn"
          disabled={clients.length === 0}
        >
          New Case
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <Input
          type="text"
          placeholder="Search cases..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="form-input max-w-xs"
          data-testid="search-input"
        />
        <Select value={stageFilter} onValueChange={(v) => { setStageFilter(v === 'all' ? '' : v); setPage(1); }}>
          <SelectTrigger className="form-input w-48" data-testid="stage-filter">
            <SelectValue placeholder="All stages" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All stages</SelectItem>
            {stages.map((stage) => (
              <SelectItem key={stage.value} value={stage.value}>{stage.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="table-header">
              <th className="text-left px-4 py-3">Client</th>
              <th className="text-left px-4 py-3">Type</th>
              <th className="text-left px-4 py-3">Stage</th>
              <th className="text-left px-4 py-3">Loan</th>
              <th className="text-left px-4 py-3">LTV</th>
              <th className="text-left px-4 py-3">Lender</th>
              <th className="text-right px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="table-row">
                  <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-6 w-24" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-12" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20 ml-auto" /></td>
                </tr>
              ))
            ) : cases.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="empty-state">
                    <h3>No cases yet</h3>
                    <p>{clients.length === 0 ? 'Add a client first to create cases' : 'Create your first mortgage case'}</p>
                    {clients.length > 0 && (
                      <Button
                        onClick={() => openDialog()}
                        className="bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
                        data-testid="empty-add-case-btn"
                      >
                        New Case
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              cases.map((caseItem) => {
                const stageInfo = getStageInfo(caseItem.stage);
                return (
                  <tr key={caseItem.id} className="table-row" data-testid={`case-row-${caseItem.id}`}>
                    <td className="px-4 py-3 font-medium text-[#111827]">
                      {caseItem.client_name}
                    </td>
                    <td className="px-4 py-3 text-[#6B7280]">
                      {mortgageTypes.find(t => t.value === caseItem.mortgage_type)?.label || caseItem.mortgage_type}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`badge ${stageInfo.badge}`}>
                        {stageInfo.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[#111827]">{formatCurrency(caseItem.loan_amount)}</td>
                    <td className="px-4 py-3 text-[#111827]">{caseItem.ltv ? `${caseItem.ltv}%` : '-'}</td>
                    <td className="px-4 py-3 text-[#6B7280]">{caseItem.lender_name || '-'}</td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/cases/${caseItem.id}`}
                        className="text-[#0E9F6E] hover:underline text-sm mr-3"
                        data-testid={`view-case-${caseItem.id}`}
                      >
                        View
                      </Link>
                      <button
                        onClick={() => openDialog(caseItem)}
                        className="text-[#0E9F6E] hover:underline text-sm mr-3"
                        data-testid={`edit-case-${caseItem.id}`}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(caseItem.id)}
                        className="text-[#EF4444] hover:underline text-sm"
                        data-testid={`delete-case-${caseItem.id}`}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-between items-center mt-4">
          <span className="text-sm text-[#6B7280]">
            Showing {((page - 1) * 20) + 1} to {Math.min(page * 20, total)} of {total} cases
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

      {/* Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingCase ? 'Edit Case' : 'New Case'}</DialogTitle>
            <DialogDescription className="sr-only">
              {editingCase ? 'Edit mortgage case details' : 'Create a new mortgage case'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-5 mt-4">
            <div className="form-grid">
              <div>
                <label className="form-label">Client <span className="text-[#0E9F6E]">*</span></label>
                <Select
                  value={formData.client_id}
                  onValueChange={(value) => setFormData({ ...formData, client_id: value })}
                  required
                >
                  <SelectTrigger className="form-input" data-testid="case-client-select">
                    <SelectValue placeholder="Select client" />
                  </SelectTrigger>
                  <SelectContent>
                    {clients.map((client) => (
                      <SelectItem key={client.id} value={client.id}>
                        {client.first_name} {client.last_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="form-label">Mortgage type</label>
                <Select
                  value={formData.mortgage_type}
                  onValueChange={(value) => setFormData({ ...formData, mortgage_type: value })}
                >
                  <SelectTrigger className="form-input" data-testid="case-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {mortgageTypes.map((type) => (
                      <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="form-grid">
              <div>
                <label className="form-label">Stage</label>
                <Select
                  value={formData.stage}
                  onValueChange={(value) => setFormData({ ...formData, stage: value })}
                >
                  <SelectTrigger className="form-input" data-testid="case-stage-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {stages.map((stage) => (
                      <SelectItem key={stage.value} value={stage.value}>{stage.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="form-label">Lender</label>
                <Select
                  value={formData.lender_id}
                  onValueChange={(value) => setFormData({ ...formData, lender_id: value })}
                >
                  <SelectTrigger className="form-input" data-testid="case-lender-select">
                    <SelectValue placeholder="Select lender" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">No lender</SelectItem>
                    {lenders.map((lender) => (
                      <SelectItem key={lender.id} value={lender.id}>{lender.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="form-grid">
              <div>
                <label className="form-label">Loan amount (£)</label>
                <Input
                  type="number"
                  value={formData.loan_amount}
                  onChange={(e) => setFormData({ ...formData, loan_amount: e.target.value })}
                  placeholder="250000"
                  className="form-input"
                  data-testid="case-loan-input"
                />
              </div>
              <div>
                <label className="form-label">Property value (£)</label>
                <Input
                  type="number"
                  value={formData.property_value}
                  onChange={(e) => setFormData({ ...formData, property_value: e.target.value })}
                  placeholder="300000"
                  className="form-input"
                  data-testid="case-property-input"
                />
              </div>
            </div>

            <div className="form-grid">
              <div>
                <label className="form-label">Term (years)</label>
                <Input
                  type="number"
                  value={formData.term_years}
                  onChange={(e) => setFormData({ ...formData, term_years: e.target.value })}
                  placeholder="25"
                  className="form-input"
                  data-testid="case-term-input"
                />
              </div>
              <div>
                <label className="form-label">Rate type</label>
                <Select
                  value={formData.rate_type}
                  onValueChange={(value) => setFormData({ ...formData, rate_type: value })}
                >
                  <SelectTrigger className="form-input" data-testid="case-rate-type-select">
                    <SelectValue placeholder="Select rate type" />
                  </SelectTrigger>
                  <SelectContent>
                    {rateTypes.map((type) => (
                      <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="form-grid">
              <div>
                <label className="form-label">Rate (%)</label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.rate_percent}
                  onChange={(e) => setFormData({ ...formData, rate_percent: e.target.value })}
                  placeholder="4.99"
                  className="form-input"
                  data-testid="case-rate-input"
                />
              </div>
              <div>
                <label className="form-label">Expected completion</label>
                <Input
                  type="date"
                  value={formData.expected_completion_date}
                  onChange={(e) => setFormData({ ...formData, expected_completion_date: e.target.value })}
                  className="form-input"
                  data-testid="case-completion-input"
                />
              </div>
            </div>

            <div>
              <label className="form-label">Notes</label>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Add any notes about this case..."
                className="form-input min-h-[100px]"
                data-testid="case-notes-input"
              />
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} className="border-[#E5E7EB]">
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={saving || !formData.client_id}
                className="bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
                data-testid="save-case-btn"
              >
                {saving ? 'Saving...' : editingCase ? 'Update Case' : 'Create Case'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
