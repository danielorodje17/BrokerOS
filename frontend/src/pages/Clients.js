import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Skeleton } from '../components/ui/skeleton';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const employmentTypes = [
  { value: 'employed', label: 'Employed' },
  { value: 'self-employed', label: 'Self-Employed' },
  { value: 'contractor', label: 'Contractor' },
  { value: 'retired', label: 'Retired' }
];

const creditProfiles = [
  { value: 'clean', label: 'Clean' },
  { value: 'minor_issues', label: 'Minor Issues' },
  { value: 'adverse', label: 'Adverse' }
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

export function Clients() {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingClient, setEditingClient] = useState(null);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    date_of_birth: '',
    ni_number: '',
    employment_type: 'employed',
    employer_name: '',
    annual_income: '',
    credit_profile: 'clean',
    consent_date: ''
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchClients();
  }, [page, search]);

  const fetchClients = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, limit: 20 });
      if (search) params.append('search', search);
      const { data } = await axios.get(`${API}/clients?${params}`, { withCredentials: true });
      setClients(data.clients);
      setTotal(data.total);
    } catch (error) {
      toast.error('Failed to load clients');
    } finally {
      setLoading(false);
    }
  };

  const openDialog = (client = null) => {
    if (client) {
      setEditingClient(client);
      setFormData({
        first_name: client.first_name || '',
        last_name: client.last_name || '',
        email: client.email || '',
        phone: client.phone || '',
        date_of_birth: client.date_of_birth || '',
        ni_number: client.ni_number || '',
        employment_type: client.employment_type || 'employed',
        employer_name: client.employer_name || '',
        annual_income: client.annual_income || '',
        credit_profile: client.credit_profile || 'clean',
        consent_date: client.consent_date || ''
      });
    } else {
      setEditingClient(null);
      setFormData({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        date_of_birth: '',
        ni_number: '',
        employment_type: 'employed',
        employer_name: '',
        annual_income: '',
        credit_profile: 'clean',
        consent_date: ''
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);

    const payload = {
      ...formData,
      annual_income: formData.annual_income ? parseFloat(formData.annual_income) : null
    };

    try {
      if (editingClient) {
        await axios.put(`${API}/clients/${editingClient.id}`, payload, { withCredentials: true });
        toast.success('Client updated');
      } else {
        await axios.post(`${API}/clients`, payload, { withCredentials: true });
        toast.success('Client added');
      }
      setDialogOpen(false);
      fetchClients();
    } catch (error) {
      toast.error(editingClient ? 'Failed to update client' : 'Failed to add client');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (clientId) => {
    if (!window.confirm('Are you sure you want to delete this client?')) return;
    try {
      await axios.delete(`${API}/clients/${clientId}`, { withCredentials: true });
      toast.success('Client deleted');
      fetchClients();
    } catch (error) {
      toast.error('Failed to delete client');
    }
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div data-testid="clients-page">
      <div className="page-header">
        <h1>Clients</h1>
        <Button
          onClick={() => openDialog()}
          className="bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
          data-testid="add-client-btn"
        >
          Add Client
        </Button>
      </div>

      {/* Search */}
      <div className="search-bar">
        <Input
          type="text"
          placeholder="Search clients..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="form-input search-input"
          data-testid="search-input"
        />
      </div>

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="table-header">
              <th className="text-left px-4 py-3">Name</th>
              <th className="text-left px-4 py-3">Email</th>
              <th className="text-left px-4 py-3">Phone</th>
              <th className="text-left px-4 py-3">Employment</th>
              <th className="text-left px-4 py-3">Income</th>
              <th className="text-left px-4 py-3">Credit</th>
              <th className="text-right px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="table-row">
                  <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-40" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-16" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20 ml-auto" /></td>
                </tr>
              ))
            ) : clients.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="empty-state">
                    <h3>No clients yet</h3>
                    <p>Add your first client to get started</p>
                    <Button
                      onClick={() => openDialog()}
                      className="bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
                      data-testid="empty-add-client-btn"
                    >
                      Add Client
                    </Button>
                  </div>
                </td>
              </tr>
            ) : (
              clients.map((client) => (
                <tr key={client.id} className="table-row" data-testid={`client-row-${client.id}`}>
                  <td className="px-4 py-3 font-medium text-[#111827]">
                    {client.first_name} {client.last_name}
                  </td>
                  <td className="px-4 py-3 text-[#6B7280]">{client.email || '-'}</td>
                  <td className="px-4 py-3 text-[#6B7280]">{client.phone || '-'}</td>
                  <td className="px-4 py-3">
                    <span className="badge badge-grey">
                      {employmentTypes.find(e => e.value === client.employment_type)?.label || client.employment_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[#111827]">{formatCurrency(client.annual_income)}</td>
                  <td className="px-4 py-3">
                    <span className={`badge ${
                      client.credit_profile === 'clean' ? 'badge-green' :
                      client.credit_profile === 'minor_issues' ? 'badge-amber' : 'badge-red'
                    }`}>
                      {creditProfiles.find(c => c.value === client.credit_profile)?.label || client.credit_profile}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => openDialog(client)}
                      className="text-[#0E9F6E] hover:underline text-sm mr-3"
                      data-testid={`edit-client-${client.id}`}
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(client.id)}
                      className="text-[#EF4444] hover:underline text-sm"
                      data-testid={`delete-client-${client.id}`}
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

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-between items-center mt-4">
          <span className="text-sm text-[#6B7280]">
            Showing {((page - 1) * 20) + 1} to {Math.min(page * 20, total)} of {total} clients
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="border-[#E5E7EB]"
              data-testid="prev-page-btn"
            >
              Previous
            </Button>
            <Button
              variant="outline"
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="border-[#E5E7EB]"
              data-testid="next-page-btn"
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingClient ? 'Edit Client' : 'Add Client'}</DialogTitle>
            <DialogDescription className="sr-only">
              {editingClient ? 'Edit client details' : 'Add a new client to your database'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-5 mt-4">
            <div className="form-grid">
              <div>
                <label className="form-label">First name <span className="text-[#0E9F6E]">*</span></label>
                <Input
                  type="text"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  required
                  className="form-input"
                  data-testid="client-first-name-input"
                />
              </div>
              <div>
                <label className="form-label">Last name <span className="text-[#0E9F6E]">*</span></label>
                <Input
                  type="text"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  required
                  className="form-input"
                  data-testid="client-last-name-input"
                />
              </div>
            </div>

            <div className="form-grid">
              <div>
                <label className="form-label">Email</label>
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="form-input"
                  data-testid="client-email-input"
                />
              </div>
              <div>
                <label className="form-label">Phone</label>
                <Input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="form-input"
                  data-testid="client-phone-input"
                />
              </div>
            </div>

            <div className="form-grid">
              <div>
                <label className="form-label">Date of birth</label>
                <Input
                  type="date"
                  value={formData.date_of_birth}
                  onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                  className="form-input"
                  data-testid="client-dob-input"
                />
              </div>
              <div>
                <label className="form-label">NI Number</label>
                <Input
                  type="text"
                  value={formData.ni_number}
                  onChange={(e) => setFormData({ ...formData, ni_number: e.target.value })}
                  placeholder="AB 12 34 56 C"
                  className="form-input"
                  data-testid="client-ni-input"
                />
              </div>
            </div>

            <div className="form-grid">
              <div>
                <label className="form-label">Employment type</label>
                <Select
                  value={formData.employment_type}
                  onValueChange={(value) => setFormData({ ...formData, employment_type: value })}
                >
                  <SelectTrigger className="form-input" data-testid="client-employment-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {employmentTypes.map((type) => (
                      <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="form-label">Employer name</label>
                <Input
                  type="text"
                  value={formData.employer_name}
                  onChange={(e) => setFormData({ ...formData, employer_name: e.target.value })}
                  className="form-input"
                  data-testid="client-employer-input"
                />
              </div>
            </div>

            <div className="form-grid">
              <div>
                <label className="form-label">Annual income (£)</label>
                <Input
                  type="number"
                  value={formData.annual_income}
                  onChange={(e) => setFormData({ ...formData, annual_income: e.target.value })}
                  placeholder="50000"
                  className="form-input"
                  data-testid="client-income-input"
                />
              </div>
              <div>
                <label className="form-label">Credit profile</label>
                <Select
                  value={formData.credit_profile}
                  onValueChange={(value) => setFormData({ ...formData, credit_profile: value })}
                >
                  <SelectTrigger className="form-input" data-testid="client-credit-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {creditProfiles.map((profile) => (
                      <SelectItem key={profile.value} value={profile.value}>{profile.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <label className="form-label">GDPR consent date</label>
              <Input
                type="date"
                value={formData.consent_date}
                onChange={(e) => setFormData({ ...formData, consent_date: e.target.value })}
                className="form-input max-w-xs"
                data-testid="client-consent-input"
              />
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => setDialogOpen(false)}
                className="border-[#E5E7EB]"
                data-testid="cancel-btn"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={saving}
                className="bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
                data-testid="save-client-btn"
              >
                {saving ? 'Saving...' : editingClient ? 'Update Client' : 'Add Client'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
