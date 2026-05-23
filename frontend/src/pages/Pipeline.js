import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Skeleton } from '../components/ui/skeleton';
import { useAuth } from '../contexts/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

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

const formatCurrency = (value) => {
  if (!value) return '-';
  return '£' + value.toLocaleString('en-GB');
};

export function Pipeline() {
  const { user } = useAuth();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCase, setSelectedCase] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [viewMode, setViewMode] = useState('kanban'); // 'kanban' | 'list'
  const [search, setSearch] = useState('');
  const [teamMembers, setTeamMembers] = useState([]);
  const [selectedBroker, setSelectedBroker] = useState('');

  useEffect(() => {
    fetchCases();
  }, []);

  useEffect(() => {
    if (user?.role === 'principal' || user?.role === 'admin') {
      axios.get(`${API}/auth/team/members`, { withCredentials: true })
        .then(({ data }) => { if (data.success) setTeamMembers(data.data); })
        .catch(() => {});
    }
  }, [user?.role]);

  const fetchCases = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/cases?limit=100`, { withCredentials: true });
      setCases(data.cases);
    } catch (error) {
      toast.error('Failed to load pipeline');
    } finally {
      setLoading(false);
    }
  };

  const updateStage = async (caseId, newStage) => {
    setUpdating(true);
    try {
      await axios.patch(`${API}/cases/${caseId}/stage?stage=${newStage}`, {}, { withCredentials: true });
      toast.success('Stage updated');
      fetchCases();
      setDialogOpen(false);
    } catch (error) {
      toast.error('Failed to update stage');
    } finally {
      setUpdating(false);
    }
  };

  const openCaseDialog = (caseItem) => {
    setSelectedCase(caseItem);
    setDialogOpen(true);
  };

  const getCasesForStage = (stage) => cases.filter(c => c.stage === stage);

  // Only show active pipeline stages (exclude completion, on_hold, declined)
  const pipelineStages = stages.filter(s => !['completion', 'on_hold', 'declined'].includes(s.value));

  const getStageInfo = (stage) => stages.find(s => s.value === stage) || { label: stage, badge: 'badge-grey' };

  // List view filtered cases — broker filter + text search
  const filteredCases = useMemo(() => {
    const base = selectedBroker ? cases.filter(c => c.assigned_broker_id === selectedBroker) : cases;
    const q = search.toLowerCase().trim();
    if (!q) return base;
    return base.filter((c) => {
      const clientName = (c.client_name || '').toLowerCase();
      const lenderName = (c.lender_name || '').toLowerCase();
      return clientName.includes(q) || lenderName.includes(q);
    });
  }, [cases, search, selectedBroker]);

  return (
    <div data-testid="pipeline-page">
      <div className="page-header">
        <h1>Deal Pipeline</h1>

        {/* View Mode Toggle */}
        <div
          className="inline-flex rounded-md border border-[#E5E7EB] overflow-hidden"
          data-testid="pipeline-view-toggle"
        >
          <button
            type="button"
            onClick={() => setViewMode('kanban')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              viewMode === 'kanban'
                ? 'bg-[#0A2342] text-white'
                : 'bg-white text-[#0A2342] hover:bg-[#F8F9FA]'
            }`}
            data-testid="view-kanban-btn"
          >
            Kanban
          </button>
          <button
            type="button"
            onClick={() => setViewMode('list')}
            className={`px-4 py-2 text-sm font-medium border-l border-[#E5E7EB] transition-colors ${
              viewMode === 'list'
                ? 'bg-[#0A2342] text-white'
                : 'bg-white text-[#0A2342] hover:bg-[#F8F9FA]'
            }`}
            data-testid="view-list-btn"
          >
            List
          </button>
        </div>
      </div>

      {/* Search bar + Broker filter — visible only in List view */}
      {viewMode === 'list' && (
        <div className="flex gap-3 mb-6 items-center flex-wrap">
          {teamMembers.length > 0 && (
            <Select
              value={selectedBroker || 'all'}
              onValueChange={(v) => setSelectedBroker(v === 'all' ? '' : v)}
            >
              <SelectTrigger className="form-input w-40" data-testid="broker-filter">
                <SelectValue placeholder="All Brokers" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Brokers</SelectItem>
                {teamMembers.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    {m.first_name} {m.last_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Input
            type="text"
            placeholder="Search by client or lender name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="form-input max-w-xs"
            data-testid="pipeline-search-input"
          />
        </div>
      )}

      {loading ? (
        viewMode === 'kanban' ? (
          <div className="kanban-board">
            {pipelineStages.map((stage) => (
              <div key={stage.value} className="kanban-column">
                <div className="kanban-column-header">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-5 w-8 rounded-full" />
                </div>
                {[1, 2].map((i) => (
                  <div key={i} className="kanban-card">
                    <Skeleton className="h-4 w-32 mb-2" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                ))}
              </div>
            ))}
          </div>
        ) : (
          <div className="card p-0 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="table-header">
                  <th className="text-left px-4 py-3">Client</th>
                  <th className="text-left px-4 py-3">Stage</th>
                  <th className="text-left px-4 py-3">Loan</th>
                  <th className="text-left px-4 py-3">Lender</th>
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="table-row">
                    <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-6 w-24" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : cases.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <h3>No cases in pipeline</h3>
            <p>Create a case to see it appear in your pipeline</p>
          </div>
        </div>
      ) : viewMode === 'kanban' ? (
        <div className="kanban-board" data-testid="kanban-board">
          {pipelineStages.map((stage) => {
            const stageCases = getCasesForStage(stage.value);
            return (
              <div key={stage.value} className="kanban-column" data-testid={`kanban-column-${stage.value}`}>
                <div className="kanban-column-header">
                  <span className="kanban-column-title">{stage.label}</span>
                  <span className="kanban-column-count">{stageCases.length}</span>
                </div>
                {stageCases.map((caseItem) => (
                  <div
                    key={caseItem.id}
                    className="kanban-card"
                    onClick={() => openCaseDialog(caseItem)}
                    data-testid={`kanban-card-${caseItem.id}`}
                  >
                    <div className="kanban-card-title">{caseItem.client_name}</div>
                    <div className="kanban-card-meta">
                      {formatCurrency(caseItem.loan_amount)}
                      {caseItem.lender_name && ` · ${caseItem.lender_name}`}
                    </div>
                  </div>
                ))}
                {stageCases.length === 0 && (
                  <div className="text-center py-8 text-sm text-[#9CA3AF]">
                    No cases
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        // List View
        <div className="card p-0 overflow-hidden" data-testid="pipeline-list-view">
          <table className="w-full">
            <thead>
              <tr className="table-header">
                <th className="text-left px-4 py-3">Client</th>
                <th className="text-left px-4 py-3">Stage</th>
                <th className="text-left px-4 py-3">Loan</th>
                <th className="text-left px-4 py-3">Lender</th>
              </tr>
            </thead>
            <tbody>
              {filteredCases.length === 0 ? (
                <tr>
                  <td colSpan={4}>
                    <div className="empty-state">
                      {search ? (
                        <>
                          <h3>No cases match your search</h3>
                          <p>
                            <button
                              onClick={() => setSearch('')}
                              className="text-[#0E9F6E] hover:underline"
                              data-testid="pipeline-clear-search-btn"
                            >
                              Clear search
                            </button>
                          </p>
                        </>
                      ) : (
                        <>
                          <h3>No cases in pipeline</h3>
                          <p>Create a case to see it appear here</p>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                filteredCases.map((caseItem) => {
                  const stageInfo = getStageInfo(caseItem.stage);
                  return (
                    <tr
                      key={caseItem.id}
                      className="table-row cursor-pointer"
                      onClick={() => openCaseDialog(caseItem)}
                      data-testid={`pipeline-list-row-${caseItem.id}`}
                    >
                      <td className="px-4 py-3 font-medium text-[#111827]">{caseItem.client_name}</td>
                      <td className="px-4 py-3">
                        <span className={`badge ${stageInfo.badge}`}>{stageInfo.label}</span>
                      </td>
                      <td className="px-4 py-3 text-[#111827]">{formatCurrency(caseItem.loan_amount)}</td>
                      <td className="px-4 py-3 text-[#6B7280]">{caseItem.lender_name || '-'}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Completed/Hold/Declined summary (only in Kanban view) */}
      {!loading && viewMode === 'kanban' && (
        <div className="grid grid-cols-3 gap-4 mt-6">
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-[#6B7280] mb-1">Completed</div>
                <div className="text-2xl font-semibold text-[#16A34A]">
                  {getCasesForStage('completion').length}
                </div>
              </div>
              <span className="badge badge-green">Done</span>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-[#6B7280] mb-1">On Hold</div>
                <div className="text-2xl font-semibold text-[#C2410C]">
                  {getCasesForStage('on_hold').length}
                </div>
              </div>
              <span className="badge badge-orange">Paused</span>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-[#6B7280] mb-1">Declined</div>
                <div className="text-2xl font-semibold text-[#DC2626]">
                  {getCasesForStage('declined').length}
                </div>
              </div>
              <span className="badge badge-red">Closed</span>
            </div>
          </div>
        </div>
      )}

      {/* Case Detail Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Case Details</DialogTitle>
            <DialogDescription className="sr-only">View and update case stage</DialogDescription>
          </DialogHeader>
          {selectedCase && (
            <div className="space-y-4 mt-4">
              <div>
                <label className="text-sm text-[#6B7280]">Client</label>
                <div className="font-medium text-[#111827]">{selectedCase.client_name}</div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-[#6B7280]">Loan Amount</label>
                  <div className="font-medium text-[#111827]">{formatCurrency(selectedCase.loan_amount)}</div>
                </div>
                <div>
                  <label className="text-sm text-[#6B7280]">LTV</label>
                  <div className="font-medium text-[#111827]">{selectedCase.ltv ? `${selectedCase.ltv}%` : '-'}</div>
                </div>
              </div>
              <div>
                <label className="text-sm text-[#6B7280]">Lender</label>
                <div className="font-medium text-[#111827]">{selectedCase.lender_name || 'Not assigned'}</div>
              </div>
              <div>
                <label className="form-label">Move to stage</label>
                <Select
                  value={selectedCase.stage}
                  onValueChange={(value) => updateStage(selectedCase.id, value)}
                  disabled={updating}
                >
                  <SelectTrigger className="form-input" data-testid="stage-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {stages.map((stage) => (
                      <SelectItem key={stage.value} value={stage.value}>{stage.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
