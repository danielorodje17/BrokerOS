import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Skeleton } from '../components/ui/skeleton';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const statuses = [
  { value: 'pending', label: 'Pending', badge: 'badge-grey' },
  { value: 'invoiced', label: 'Invoiced', badge: 'badge-blue' },
  { value: 'received', label: 'Received', badge: 'badge-green' },
  { value: 'overdue', label: 'Overdue', badge: 'badge-red' },
  { value: 'clawback_risk', label: 'Clawback Risk', badge: 'badge-amber' }
];

const formatCurrency = (value) => {
  if (!value) return '-';
  return '£' + value.toLocaleString('en-GB');
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-GB');
};

// Clock icon component
const ClockIcon = () => (
  <svg className="w-5 h-5 text-[#D97706]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

// Alert triangle icon component
const AlertTriangleIcon = () => (
  <svg className="w-5 h-5 text-[#EF4444]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

export function Commissions() {
  const [commissions, setCommissions] = useState([]);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingCommission, setEditingCommission] = useState(null);
  const [formData, setFormData] = useState({
    case_id: '',
    expected_amount: '',
    expected_payment_date: '',
    received_amount: '',
    received_date: '',
    status: 'pending',
    clawback_risk_until: ''
  });
  const [saving, setSaving] = useState(false);
  const [generatingInvoice, setGeneratingInvoice] = useState(null);

  // Summary stats
  const [summary, setSummary] = useState({ pending: 0, received: 0 });

  // Reminders state
  const [reminders, setReminders] = useState({ due_soon: [], overdue: [] });
  const [remindersDismissed, setRemindersDismissed] = useState(false);
  const [highlightedRow, setHighlightedRow] = useState(null);
  const tableRef = useRef(null);

  useEffect(() => {
    fetchData();
  }, [page, statusFilter]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, limit: 20 });
      if (statusFilter) params.append('status', statusFilter);

      const [commissionsRes, casesRes, remindersRes] = await Promise.all([
        axios.get(`${API}/commissions?${params}`, { withCredentials: true }),
        axios.get(`${API}/cases?limit=100`, { withCredentials: true }),
        axios.get(`${API}/commissions/reminders`, { withCredentials: true })
      ]);

      setCommissions(commissionsRes.data.commissions);
      setTotal(commissionsRes.data.total);
      setCases(casesRes.data.cases);

      // Set reminders
      if (remindersRes.data.success) {
        setReminders(remindersRes.data.data);
      }

      // Calculate summary
      const allCommissions = await axios.get(`${API}/commissions?limit=1000`, { withCredentials: true });
      const pending = allCommissions.data.commissions
        .filter(c => c.status === 'pending' || c.status === 'invoiced')
        .reduce((sum, c) => sum + (c.expected_amount || 0), 0);
      const received = allCommissions.data.commissions
        .filter(c => c.status === 'received')
        .reduce((sum, c) => sum + (c.received_amount || 0), 0);
      setSummary({ pending, received });
    } catch (error) {
      toast.error('Failed to load commissions');
    } finally {
      setLoading(false);
    }
  };

  const scrollToAndHighlight = useCallback((commissionId) => {
    // First, clear any search/filter to ensure the row is visible
    const row = document.querySelector(`[data-testid="commission-row-${commissionId}"]`);
    if (row) {
      row.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setHighlightedRow(commissionId);
      setTimeout(() => setHighlightedRow(null), 2000);
    }
  }, []);

  const openDialog = (commission = null) => {
    if (commission) {
      setEditingCommission(commission);
      setFormData({
        case_id: commission.case_id || '',
        expected_amount: commission.expected_amount || '',
        expected_payment_date: commission.expected_payment_date || '',
        received_amount: commission.received_amount || '',
        received_date: commission.received_date || '',
        status: commission.status || 'pending',
        clawback_risk_until: commission.clawback_risk_until || ''
      });
    } else {
      setEditingCommission(null);
      setFormData({
        case_id: '',
        expected_amount: '',
        expected_payment_date: '',
        received_amount: '',
        received_date: '',
        status: 'pending',
        clawback_risk_until: ''
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);

    const payload = {
      ...formData,
      expected_amount: formData.expected_amount ? parseFloat(formData.expected_amount) : null,
      received_amount: formData.received_amount ? parseFloat(formData.received_amount) : null
    };

    try {
      if (editingCommission) {
        await axios.put(`${API}/commissions/${editingCommission.id}`, payload, { withCredentials: true });
        toast.success('Commission updated');
      } else {
        await axios.post(`${API}/commissions`, payload, { withCredentials: true });
        toast.success('Commission added');
      }
      setDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(editingCommission ? 'Failed to update commission' : 'Failed to add commission');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (commissionId) => {
    if (!window.confirm('Are you sure you want to delete this commission record?')) return;
    try {
      await axios.delete(`${API}/commissions/${commissionId}`, { withCredentials: true });
      toast.success('Commission deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete commission');
    }
  };

  const getStatusInfo = (status) => statuses.find(s => s.value === status) || { label: status, badge: 'badge-grey' };

  const handleGenerateInvoice = async (commissionId) => {
    setGeneratingInvoice(commissionId);
    try {
      const response = await axios.get(`${API}/commissions/${commissionId}/invoice`, {
        withCredentials: true,
        responseType: 'blob'
      });

      // Get invoice number from response header
      const invoiceNumber = response.headers['x-invoice-number'] || 'invoice';

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${invoiceNumber}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success(`Invoice ${invoiceNumber} downloaded`);
    } catch (error) {
      console.error('Invoice generation error:', error);
      toast.error('Invoice generation failed — please try again');
    } finally {
      setGeneratingInvoice(null);
    }
  };

  // Filter commissions by search (client name, lender name, and invoice/reference number)
  const filteredCommissions = commissions.filter(comm => {
    if (!search) return true;
    const searchLower = search.toLowerCase().trim();
    const clientName = (comm.client_name || '').toLowerCase();
    const lenderName = (comm.lender_name || '').toLowerCase();
    const invoiceNumber = (comm.invoice_number || '').toLowerCase();
    return clientName.includes(searchLower)
      || lenderName.includes(searchLower)
      || invoiceNumber.includes(searchLower);
  });

  const totalPages = Math.ceil(total / 20);
  const hasReminders = !remindersDismissed && (reminders.due_soon.length > 0 || reminders.overdue.length > 0);

  return (
    <div data-testid="commissions-page">
      <div className="page-header">
        <h1>Commission Tracker</h1>
        <Button
          onClick={() => openDialog()}
          className="bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
          data-testid="add-commission-btn"
          disabled={cases.length === 0}
        >
          Add Commission
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        <div className="card">
          <div className="stat-card-label">Pending / Invoiced</div>
          <div className="stat-card-value">{formatCurrency(summary.pending)}</div>
        </div>
        <div className="card">
          <div className="stat-card-label">Received This Year</div>
          <div className="stat-card-value text-[#16A34A]">{formatCurrency(summary.received)}</div>
        </div>
      </div>

      {/* Reminders Banner */}
      {hasReminders && (
        <div className="mb-6 relative" data-testid="reminders-banner">
          {/* Dismiss button */}
          <button
            onClick={() => setRemindersDismissed(true)}
            className="absolute top-2 right-2 z-10 text-[#6B7280] hover:text-[#111827] p-1"
            data-testid="dismiss-reminders-btn"
            aria-label="Dismiss reminders"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>

          <div className={`grid gap-4 ${reminders.due_soon.length > 0 && reminders.overdue.length > 0 ? 'md:grid-cols-2' : 'grid-cols-1'}`}>
            {/* Due Soon Panel */}
            {reminders.due_soon.length > 0 && (
              <div
                className="bg-[#FEF3C7] border border-[#F59E0B] rounded-lg p-4"
                data-testid="due-soon-panel"
              >
                <div className="flex items-center gap-2 mb-3">
                  <ClockIcon />
                  <h3 className="font-semibold text-[#D97706]">Due Soon</h3>
                </div>
                <div className="space-y-2">
                  {reminders.due_soon.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => scrollToAndHighlight(item.id)}
                      className="block w-full text-left text-sm text-[#92400E] hover:text-[#78350F] hover:underline"
                      data-testid={`reminder-due-soon-${item.id}`}
                    >
                      {item.client_name} — {item.lender_name} — {formatCurrency(item.expected_amount)} — due in {item.days_until_due} day{item.days_until_due !== 1 ? 's' : ''}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Overdue Panel */}
            {reminders.overdue.length > 0 && (
              <div
                className="bg-[#FEF2F2] border border-[#EF4444] rounded-lg p-4"
                data-testid="overdue-panel"
              >
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangleIcon />
                  <h3 className="font-semibold text-[#EF4444]">Overdue</h3>
                </div>
                <div className="space-y-2">
                  {reminders.overdue.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => scrollToAndHighlight(item.id)}
                      className="block w-full text-left text-sm text-[#991B1B] hover:text-[#7F1D1D] hover:underline"
                      data-testid={`reminder-overdue-${item.id}`}
                    >
                      {item.client_name} — {item.lender_name} — {formatCurrency(item.expected_amount)} — {item.days_overdue} day{item.days_overdue !== 1 ? 's' : ''} overdue
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Filter and Search */}
      <div className="flex gap-4 mb-6">
        <Input
          type="text"
          placeholder="Search by client, lender or invoice #..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="form-input max-w-xs"
          data-testid="commission-search-input"
        />
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v === 'all' ? '' : v); setPage(1); }}>
          <SelectTrigger className="form-input w-48" data-testid="status-filter">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {statuses.map((status) => (
              <SelectItem key={status.value} value={status.value}>{status.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="card p-0 overflow-hidden" ref={tableRef}>
        <table className="w-full">
          <thead>
            <tr className="table-header">
              <th className="text-left px-4 py-3">Client</th>
              <th className="text-left px-4 py-3">Lender</th>
              <th className="text-left px-4 py-3">Loan</th>
              <th className="text-left px-4 py-3">Expected</th>
              <th className="text-left px-4 py-3">Received</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-right px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="table-row">
                  <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-6 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20 ml-auto" /></td>
                </tr>
              ))
            ) : filteredCommissions.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="empty-state">
                    {search ? (
                      <>
                        <h3>No commissions match your search</h3>
                        <p>
                          <button
                            onClick={() => setSearch('')}
                            className="text-[#0E9F6E] hover:underline"
                          >
                            Clear search
                          </button>
                        </p>
                      </>
                    ) : (
                      <>
                        <h3>No commission records</h3>
                        <p>{cases.length === 0 ? 'Create a case first to track commissions' : 'Add commission records to track payments'}</p>
                        {cases.length > 0 && (
                          <Button
                            onClick={() => openDialog()}
                            className="bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
                            data-testid="empty-add-commission-btn"
                          >
                            Add Commission
                          </Button>
                        )}
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              filteredCommissions.map((commission) => {
                const statusInfo = getStatusInfo(commission.status);
                const isHighlighted = highlightedRow === commission.id;
                return (
                  <tr
                    key={commission.id}
                    className={`table-row transition-colors duration-300 ${isHighlighted ? 'bg-yellow-100' : ''}`}
                    data-testid={`commission-row-${commission.id}`}
                  >
                    <td className="px-4 py-3 font-medium text-[#111827]">{commission.client_name}</td>
                    <td className="px-4 py-3 text-[#6B7280]">{commission.lender_name || '-'}</td>
                    <td className="px-4 py-3 text-[#111827]">{formatCurrency(commission.loan_amount)}</td>
                    <td className="px-4 py-3">
                      <div className="text-[#111827]">{formatCurrency(commission.expected_amount)}</div>
                      <div className="text-xs text-[#6B7280]">{formatDate(commission.expected_payment_date)}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-[#111827]">{formatCurrency(commission.received_amount)}</div>
                      <div className="text-xs text-[#6B7280]">{formatDate(commission.received_date)}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`badge ${statusInfo.badge}`}>{statusInfo.label}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleGenerateInvoice(commission.id)}
                        disabled={generatingInvoice === commission.id}
                        className="text-[#0A2342] hover:underline text-sm mr-3 disabled:opacity-50"
                        data-testid={`generate-invoice-${commission.id}`}
                      >
                        {generatingInvoice === commission.id ? (
                          <span className="inline-flex items-center">
                            <span className="loading-spinner mr-1 w-3 h-3"></span>
                            Generating...
                          </span>
                        ) : (
                          'Generate Invoice'
                        )}
                      </button>
                      <button
                        onClick={() => openDialog(commission)}
                        className="text-[#0E9F6E] hover:underline text-sm mr-3"
                        data-testid={`edit-commission-${commission.id}`}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(commission.id)}
                        className="text-[#EF4444] hover:underline text-sm"
                        data-testid={`delete-commission-${commission.id}`}
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
            Showing {((page - 1) * 20) + 1} to {Math.min(page * 20, total)} of {total} records
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
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingCommission ? 'Edit Commission' : 'Add Commission'}</DialogTitle>
            <DialogDescription className="sr-only">
              {editingCommission ? 'Edit commission record' : 'Add a new commission record'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-5 mt-4">
            <div>
              <label className="form-label">Case <span className="text-[#0E9F6E]">*</span></label>
              <Select
                value={formData.case_id}
                onValueChange={(value) => setFormData({ ...formData, case_id: value })}
                required
              >
                <SelectTrigger className="form-input" data-testid="commission-case-select">
                  <SelectValue placeholder="Select case" />
                </SelectTrigger>
                <SelectContent>
                  {cases.map((caseItem) => (
                    <SelectItem key={caseItem.id} value={caseItem.id}>
                      {caseItem.client_name} - {formatCurrency(caseItem.loan_amount)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="form-grid">
              <div>
                <label className="form-label">Expected amount (£)</label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.expected_amount}
                  onChange={(e) => setFormData({ ...formData, expected_amount: e.target.value })}
                  placeholder="1500.00"
                  className="form-input"
                  data-testid="expected-amount-input"
                />
              </div>
              <div>
                <label className="form-label">Expected date</label>
                <Input
                  type="date"
                  value={formData.expected_payment_date}
                  onChange={(e) => setFormData({ ...formData, expected_payment_date: e.target.value })}
                  className="form-input"
                  data-testid="expected-date-input"
                />
              </div>
            </div>

            <div className="form-grid">
              <div>
                <label className="form-label">Received amount (£)</label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.received_amount}
                  onChange={(e) => setFormData({ ...formData, received_amount: e.target.value })}
                  placeholder="1500.00"
                  className="form-input"
                  data-testid="received-amount-input"
                />
              </div>
              <div>
                <label className="form-label">Received date</label>
                <Input
                  type="date"
                  value={formData.received_date}
                  onChange={(e) => setFormData({ ...formData, received_date: e.target.value })}
                  className="form-input"
                  data-testid="received-date-input"
                />
              </div>
            </div>

            <div className="form-grid">
              <div>
                <label className="form-label">Status</label>
                <Select
                  value={formData.status}
                  onValueChange={(value) => setFormData({ ...formData, status: value })}
                >
                  <SelectTrigger className="form-input" data-testid="commission-status-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {statuses.map((status) => (
                      <SelectItem key={status.value} value={status.value}>{status.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="form-label">Clawback risk until</label>
                <Input
                  type="date"
                  value={formData.clawback_risk_until}
                  onChange={(e) => setFormData({ ...formData, clawback_risk_until: e.target.value })}
                  className="form-input"
                  data-testid="clawback-date-input"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} className="border-[#E5E7EB]">
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={saving || !formData.case_id}
                className="bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
                data-testid="save-commission-btn"
              >
                {saving ? 'Saving...' : editingCommission ? 'Update' : 'Add Commission'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
