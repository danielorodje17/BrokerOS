import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Skeleton } from '../components/ui/skeleton';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const stages = [
  { value: 'new_enquiry', label: 'New Enquiry' },
  { value: 'fact_find', label: 'Fact Find' },
  { value: 'aip_submitted', label: 'AIP Submitted' },
  { value: 'aip_received', label: 'AIP Received' },
  { value: 'full_application', label: 'Full Application' },
  { value: 'valuation', label: 'Valuation' },
  { value: 'offer', label: 'Mortgage Offer' },
  { value: 'exchange', label: 'Exchange' },
  { value: 'completion', label: 'Completion' },
  { value: 'on_hold', label: 'On Hold' },
  { value: 'declined', label: 'Declined' }
];

const formatCurrency = (value) => {
  if (!value) return '-';
  return '£' + value.toLocaleString('en-GB');
};

export function Pipeline() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCase, setSelectedCase] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    fetchCases();
  }, []);

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

  return (
    <div data-testid="pipeline-page">
      <div className="page-header">
        <h1>Deal Pipeline</h1>
      </div>

      {loading ? (
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
      ) : cases.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <h3>No cases in pipeline</h3>
            <p>Create a case to see it appear in your pipeline</p>
          </div>
        </div>
      ) : (
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
      )}

      {/* Completed/Hold/Declined summary */}
      {!loading && (
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
