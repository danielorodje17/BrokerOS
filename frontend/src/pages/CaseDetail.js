import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Skeleton } from '../components/ui/skeleton';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const mortgageTypes = {
  residential: 'Residential',
  btl: 'Buy to Let',
  remortgage: 'Remortgage',
  product_transfer: 'Product Transfer',
  bridging: 'Bridging'
};

const stages = {
  new_enquiry: { label: 'New Enquiry', badge: 'badge-grey' },
  fact_find: { label: 'Fact Find', badge: 'badge-grey' },
  aip_submitted: { label: 'AIP Submitted', badge: 'badge-amber' },
  aip_received: { label: 'AIP Received', badge: 'badge-amber' },
  full_application: { label: 'Full Application', badge: 'badge-blue' },
  valuation: { label: 'Valuation', badge: 'badge-blue' },
  offer: { label: 'Mortgage Offer', badge: 'badge-teal' },
  exchange: { label: 'Exchange', badge: 'badge-teal' },
  completion: { label: 'Completion', badge: 'badge-green' },
  on_hold: { label: 'On Hold', badge: 'badge-orange' },
  declined: { label: 'Declined', badge: 'badge-red' }
};

const formatCurrency = (value) => {
  if (!value) return '-';
  return '£' + value.toLocaleString('en-GB');
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-GB');
};

// Format relative time (e.g., "2 hours ago", "yesterday", "3 days ago")
const formatRelativeTime = (dateStr) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} week${Math.floor(diffDays / 7) !== 1 ? 's' : ''} ago`;
  return date.toLocaleDateString('en-GB');
};

// Borrower Strength Score classification → colour
const SCORE_COLOURS = {
  Strong: { hex: '#10B981', badge: 'bg-[#D1FAE5] text-[#065F46]' },
  Good:   { hex: '#0E9F6E', badge: 'bg-[#CCFBF1] text-[#115E59]' },
  Fair:   { hex: '#F59E0B', badge: 'bg-[#FEF3C7] text-[#92400E]' },
  Weak:   { hex: '#EF4444', badge: 'bg-[#FEE2E2] text-[#991B1B]' },
};

const BREAKDOWN_LABELS = {
  employment: 'Employment',
  income: 'Income',
  credit: 'Credit Profile',
  gdpr: 'Consent on File',
  documents: 'Documents',
};

export function CaseDetail() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState(null);
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notesLoading, setNotesLoading] = useState(true);
  const [noteContent, setNoteContent] = useState('');
  const [addingNote, setAddingNote] = useState(false);
  const [score, setScore] = useState(null);
  const [scoreLoading, setScoreLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [matchResult, setMatchResult] = useState(null);  // {matches, eligible_count, total_lenders, message}
  const [matchLoading, setMatchLoading] = useState(false);
  const [selectingLenderId, setSelectingLenderId] = useState(null);

  const fetchCase = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/cases/${caseId}`, { withCredentials: true });
      setCaseData(data.data);
    } catch (error) {
      toast.error('Failed to load case');
      navigate('/cases');
    } finally {
      setLoading(false);
    }
  }, [caseId, navigate]);

  const fetchNotes = useCallback(async () => {
    setNotesLoading(true);
    try {
      const { data } = await axios.get(`${API}/notes?case_id=${caseId}`, { withCredentials: true });
      setNotes(data.data);
    } catch (error) {
      console.error('Failed to load notes:', error);
    } finally {
      setNotesLoading(false);
    }
  }, [caseId]);

  const fetchScore = useCallback(async (clientId) => {
    if (!clientId) return;
    setScoreLoading(true);
    try {
      const { data } = await axios.post(
        `${API}/ai/borrower-score`,
        { client_id: clientId },
        { withCredentials: true }
      );
      setScore(data.data);
    } catch (error) {
      toast.error('Failed to compute borrower score');
    } finally {
      setScoreLoading(false);
    }
  }, []);

  const fetchMatches = useCallback(async () => {
    setMatchLoading(true);
    try {
      const { data } = await axios.post(
        `${API}/ai/lender-match`,
        { case_id: caseId },
        { withCredentials: true }
      );
      setMatchResult(data.data);
    } catch (error) {
      toast.error('Lender matching failed — please try again');
    } finally {
      setMatchLoading(false);
    }
  }, [caseId]);

  const selectLender = useCallback(async (lenderId, lenderName) => {
    setSelectingLenderId(lenderId);
    try {
      const { data } = await axios.patch(
        `${API}/cases/${caseId}/lender?lender_id=${lenderId}`,
        null,
        { withCredentials: true }
      );
      // Optimistically update case data with new lender
      setCaseData(prev => prev ? { ...prev, lender_id: lenderId, lender: data.data.lender } : prev);
      toast.success(`Lender updated to ${lenderName}`);
    } catch (error) {
      toast.error('Failed to update lender');
    } finally {
      setSelectingLenderId(null);
    }
  }, [caseId]);

  useEffect(() => {
    fetchCase();
    fetchNotes();
  }, [fetchCase, fetchNotes]);

  useEffect(() => {
    if (caseData?.client?.id) {
      fetchScore(caseData.client.id);
    }
  }, [caseData?.client?.id, fetchScore]);

  const handleAddNote = async () => {
    if (!noteContent.trim()) return;
    if (noteContent.length > 2000) {
      toast.error('Note exceeds 2000 characters');
      return;
    }

    setAddingNote(true);
    try {
      const { data } = await axios.post(`${API}/notes`, {
        case_id: caseId,
        content: noteContent.trim()
      }, { withCredentials: true });
      
      // Prepend new note to the list
      setNotes(prev => [data, ...prev]);
      setNoteContent('');
      toast.success('Note added');
    } catch (error) {
      toast.error('Failed to add note');
    } finally {
      setAddingNote(false);
    }
  };

  const isOverLimit = noteContent.length > 2000;

  const stageInfo = caseData ? stages[caseData.stage] || { label: caseData.stage, badge: 'badge-grey' } : {};

  if (loading) {
    return (
      <div data-testid="case-detail-page">
        <div className="page-header">
          <Skeleton className="h-8 w-48" />
        </div>
        <div className="card">
          <Skeleton className="h-6 w-32 mb-4" />
          <div className="grid grid-cols-2 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="case-detail-page">
      {/* Header */}
      <div className="page-header">
        <div className="flex items-center gap-4">
          <Link 
            to="/cases" 
            className="text-[#6B7280] hover:text-[#111827] text-sm"
            data-testid="back-to-cases"
          >
            ← Back to Cases
          </Link>
          <h1>{caseData.client?.first_name} {caseData.client?.last_name}</h1>
          <span className={`badge ${stageInfo.badge}`}>{stageInfo.label}</span>
        </div>
        <Link to={`/cases`}>
          <Button
            variant="outline"
            className="border-[#E5E7EB]"
            data-testid="edit-case-btn"
            onClick={(e) => {
              e.preventDefault();
              // Could navigate to edit modal or page
              navigate('/cases');
            }}
          >
            Edit Case
          </Button>
        </Link>
      </div>

      {/* Tabs */}
      <div className="border-b border-[#E5E7EB] mb-6" data-testid="case-detail-tabs">
        <nav className="flex gap-6 -mb-px">
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            data-testid="tab-overview"
            className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'overview'
                ? 'border-[#0E9F6E] text-[#0A2342]'
                : 'border-transparent text-[#6B7280] hover:text-[#111827]'
            }`}
          >
            Overview
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('lender-match')}
            data-testid="tab-lender-match"
            className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'lender-match'
                ? 'border-[#0E9F6E] text-[#0A2342]'
                : 'border-transparent text-[#6B7280] hover:text-[#111827]'
            }`}
          >
            AI Lender Match
          </button>
        </nav>
      </div>

      {activeTab === 'overview' && (
      <>

      {/* Case Details */}
      <div className="card mb-6">
        <h2 className="text-lg font-semibold text-[#111827] mb-4">Case Details</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
          <div>
            <div className="text-sm text-[#6B7280] mb-1">Mortgage Type</div>
            <div className="text-[#111827] font-medium">
              {mortgageTypes[caseData.mortgage_type] || caseData.mortgage_type}
            </div>
          </div>
          <div>
            <div className="text-sm text-[#6B7280] mb-1">Loan Amount</div>
            <div className="text-[#111827] font-medium">{formatCurrency(caseData.loan_amount)}</div>
          </div>
          <div>
            <div className="text-sm text-[#6B7280] mb-1">Property Value</div>
            <div className="text-[#111827] font-medium">{formatCurrency(caseData.property_value)}</div>
          </div>
          <div>
            <div className="text-sm text-[#6B7280] mb-1">LTV</div>
            <div className="text-[#111827] font-medium">{caseData.ltv ? `${caseData.ltv}%` : '-'}</div>
          </div>
          <div>
            <div className="text-sm text-[#6B7280] mb-1">Term</div>
            <div className="text-[#111827] font-medium">{caseData.term_years ? `${caseData.term_years} years` : '-'}</div>
          </div>
          <div>
            <div className="text-sm text-[#6B7280] mb-1">Lender</div>
            <div className="text-[#111827] font-medium">{caseData.lender?.name || '-'}</div>
          </div>
          <div>
            <div className="text-sm text-[#6B7280] mb-1">Rate Type</div>
            <div className="text-[#111827] font-medium capitalize">{caseData.rate_type || '-'}</div>
          </div>
          <div>
            <div className="text-sm text-[#6B7280] mb-1">Rate</div>
            <div className="text-[#111827] font-medium">{caseData.rate_percent ? `${caseData.rate_percent}%` : '-'}</div>
          </div>
          <div>
            <div className="text-sm text-[#6B7280] mb-1">Expected Completion</div>
            <div className="text-[#111827] font-medium">{formatDate(caseData.expected_completion_date)}</div>
          </div>
        </div>
        {caseData.notes && (
          <div className="mt-6 pt-6 border-t border-[#E5E7EB]">
            <div className="text-sm text-[#6B7280] mb-1">Case Notes</div>
            <div className="text-[#111827]">{caseData.notes}</div>
          </div>
        )}
      </div>

      {/* Client Details */}
      {caseData.client && (
        <div className="card mb-6">
          <h2 className="text-lg font-semibold text-[#111827] mb-4">Client Details</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
            <div>
              <div className="text-sm text-[#6B7280] mb-1">Name</div>
              <div className="text-[#111827] font-medium">
                {caseData.client.first_name} {caseData.client.last_name}
              </div>
            </div>
            <div>
              <div className="text-sm text-[#6B7280] mb-1">Email</div>
              <div className="text-[#111827]">{caseData.client.email || '-'}</div>
            </div>
            <div>
              <div className="text-sm text-[#6B7280] mb-1">Phone</div>
              <div className="text-[#111827]">{caseData.client.phone || '-'}</div>
            </div>
            <div>
              <div className="text-sm text-[#6B7280] mb-1">Employment</div>
              <div className="text-[#111827] capitalize">{caseData.client.employment_type?.replace('_', ' ') || '-'}</div>
            </div>
            <div>
              <div className="text-sm text-[#6B7280] mb-1">Annual Income</div>
              <div className="text-[#111827]">{formatCurrency(caseData.client.annual_income)}</div>
            </div>
            <div>
              <div className="text-sm text-[#6B7280] mb-1">Credit Profile</div>
              <div className="text-[#111827] capitalize">{caseData.client.credit_profile?.replace('_', ' ') || '-'}</div>
            </div>
          </div>
        </div>
      )}

      {/* Borrower Strength Score */}
      {caseData.client && (
        <div className="card mb-6" data-testid="borrower-score-card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-[#111827]">Borrower Strength Score</h2>
            <Button
              variant="outline"
              className="border-[#E5E7EB] text-sm"
              onClick={() => fetchScore(caseData.client.id)}
              disabled={scoreLoading}
              data-testid="recalculate-score-btn"
            >
              {scoreLoading ? 'Calculating...' : 'Recalculate'}
            </Button>
          </div>

          {scoreLoading && !score ? (
            <div className="space-y-4">
              <div className="flex items-center gap-6">
                <Skeleton className="h-20 w-32" />
                <Skeleton className="h-6 w-24" />
              </div>
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ) : score ? (
            <>
              {/* Top: big score + classification badge */}
              <div className="flex items-baseline gap-4 mb-4">
                <div
                  className="text-6xl font-bold leading-none"
                  style={{ color: SCORE_COLOURS[score.classification]?.hex || '#111827' }}
                  data-testid="borrower-score-value"
                >
                  {score.score}
                </div>
                <div className="text-2xl text-[#6B7280]">/ 100</div>
                <span
                  className={`badge ml-2 ${SCORE_COLOURS[score.classification]?.badge || 'badge-grey'}`}
                  data-testid="borrower-score-classification"
                >
                  {score.classification}
                </span>
              </div>

              {/* Progress bar */}
              <div className="w-full h-3 rounded-full bg-[#E5E7EB] overflow-hidden mb-6" data-testid="borrower-score-progress">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${score.score}%`,
                    backgroundColor: SCORE_COLOURS[score.classification]?.hex || '#0E9F6E',
                  }}
                />
              </div>

              {/* AI summary */}
              <div
                className="bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg p-4 mb-6"
                data-testid="borrower-score-summary"
              >
                <div className="text-xs uppercase tracking-wide text-[#6B7280] mb-2 font-semibold">
                  AI Summary
                </div>
                <p className="text-[#111827] whitespace-pre-wrap leading-relaxed">{score.summary}</p>
              </div>

              {/* Breakdown */}
              <div className="space-y-3" data-testid="borrower-score-breakdown">
                <div className="text-xs uppercase tracking-wide text-[#6B7280] font-semibold mb-2">
                  Score Breakdown
                </div>
                {Object.entries(score.breakdown).map(([key, item]) => {
                  const pct = item.max > 0 ? (item.points / item.max) * 100 : 0;
                  return (
                    <div
                      key={key}
                      className="flex items-center gap-4"
                      data-testid={`breakdown-row-${key}`}
                    >
                      <div className="w-40 shrink-0">
                        <div className="text-sm font-medium text-[#111827]">
                          {BREAKDOWN_LABELS[key] || key}
                        </div>
                        <div className="text-xs text-[#6B7280]">{item.label}</div>
                      </div>
                      <div className="flex-1 h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#0E9F6E] rounded-full"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <div className="w-20 text-right text-sm font-medium text-[#111827] shrink-0">
                        {item.points} / {item.max}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="text-center py-8 text-[#6B7280]" data-testid="borrower-score-empty">
              Unable to calculate score.
            </div>
          )}
        </div>
      )}

      {/* Case Notes Timeline */}
      <div className="card" data-testid="case-notes-section">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-[#111827]">
            Case Notes
            <span className="ml-2 badge badge-grey" data-testid="notes-count">{notes.length}</span>
          </h2>
        </div>

        {/* Add note form */}
        <div className="mb-6">
          <div className="relative">
            <Textarea
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              placeholder="Add a note..."
              className="form-input min-h-[100px] pr-20"
              maxLength={2000}
              data-testid="note-textarea"
            />
            <div className={`absolute bottom-3 right-3 text-xs ${isOverLimit ? 'text-[#EF4444] font-medium' : 'text-[#6B7280]'}`} data-testid="note-char-count">
              {noteContent.length} / 2000
            </div>
          </div>
          <div className="flex justify-end mt-3">
            <Button
              onClick={handleAddNote}
              disabled={!noteContent.trim() || addingNote || isOverLimit}
              className="bg-[#0A2342] hover:bg-[#0d2d52] text-white disabled:bg-[#D1D5DB] disabled:text-[#9CA3AF]"
              data-testid="add-note-btn"
            >
              {addingNote ? 'Adding...' : 'Add Note'}
            </Button>
          </div>
        </div>

        {/* Notes list */}
        {notesLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="border border-[#E5E7EB] rounded-lg p-4">
                <Skeleton className="h-4 w-32 mb-2" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4 mt-1" />
              </div>
            ))}
          </div>
        ) : notes.length === 0 ? (
          <div className="text-center py-12" data-testid="notes-empty-state">
            <svg
              className="mx-auto h-12 w-12 text-[#9CA3AF]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <h3 className="mt-4 text-base font-semibold text-[#111827]">No notes yet</h3>
            <p className="mt-1 text-sm text-[#6B7280]">Add the first note above</p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="notes-list">
            {notes.map((note) => (
              <div
                key={note.id}
                className="border border-[#E5E7EB] rounded-lg p-4"
                data-testid={`note-${note.id}`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-medium text-[#0E9F6E]" data-testid={`note-author-${note.id}`}>
                    {note.author_name || 'Unknown'}
                  </span>
                  <span className="text-sm text-[#6B7280]" data-testid={`note-time-${note.id}`}>
                    {formatRelativeTime(note.created_at)}
                  </span>
                </div>
                <p className="text-[#111827] whitespace-pre-wrap" data-testid={`note-content-${note.id}`}>
                  {note.content}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
      </>
      )}

      {activeTab === 'lender-match' && (
        <div data-testid="lender-match-tab-content">
          <div className="card mb-6">
            <div className="flex items-start justify-between mb-2">
              <h2 className="text-lg font-semibold text-[#111827]">AI Lender Match</h2>
              {matchResult && (
                <span className="text-sm text-[#6B7280]" data-testid="lender-match-summary">
                  {matchResult.eligible_count} lender{matchResult.eligible_count !== 1 ? 's' : ''} matched from your panel of {matchResult.total_lenders}
                </span>
              )}
            </div>
            <p className="text-sm text-[#6B7280] mb-4">
              Get an AI-ranked shortlist of suitable lenders from your panel for this case.
            </p>

            {matchLoading ? (
              <div className="flex items-center gap-3" data-testid="lender-match-loading">
                <svg className="animate-spin h-5 w-5 text-[#0E9F6E]" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" className="opacity-25" />
                  <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" fill="none" />
                </svg>
                <span className="italic text-[#6B7280]">Analysing your lender panel…</span>
              </div>
            ) : (
              <Button
                onClick={fetchMatches}
                className="bg-[#0E9F6E] hover:bg-[#0B8A5E] text-white"
                data-testid="find-best-lenders-btn"
              >
                {matchResult ? 'Find Best Lenders Again' : 'Find Best Lenders'}
              </Button>
            )}
          </div>

          {/* Empty state */}
          {matchResult && matchResult.matches.length === 0 && (
            <div
              className="bg-[#F3F4F6] border border-[#E5E7EB] rounded-md p-6"
              data-testid="lender-match-empty"
            >
              <p className="text-[#111827] font-medium mb-2">No suitable lenders found</p>
              <p className="text-sm text-[#6B7280] mb-2">{matchResult.message}</p>
              <p className="text-sm text-[#6B7280]">
                Review case LTV, loan amount, or client profile — or add more lenders to your panel.
              </p>
            </div>
          )}

          {/* Results */}
          {matchResult && matchResult.matches.length > 0 && (
            <div className="space-y-3" data-testid="lender-match-results">
              {matchResult.matches.map((m) => {
                const isCurrent = caseData.lender_id === m.lender_id;
                const lenderSelected = !!caseData.lender_id;
                const leftBorder =
                  isCurrent
                    ? 'border-l-4 border-l-[#0E9F6E]'
                    : m.rank === 1
                    ? 'border-l-4 border-l-[#0E9F6E]'
                    : m.rank === 2
                    ? 'border-l-4 border-l-[#D1D5DB]'
                    : '';

                return (
                  <div
                    key={m.lender_id}
                    className={`bg-white border border-[#E5E7EB] rounded-md p-4 flex items-start gap-4 ${leftBorder}`}
                    data-testid={`lender-match-card-${m.rank}`}
                  >
                    {/* Rank badge */}
                    <div className="shrink-0">
                      <div
                        className="w-9 h-9 rounded-full bg-[#0A2342] text-white flex items-center justify-center font-semibold"
                        data-testid={`rank-badge-${m.rank}`}
                      >
                        {m.rank}
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline gap-3 flex-wrap mb-1">
                        <span className="font-bold text-[16px] text-[#111827]" data-testid={`lender-name-${m.rank}`}>
                          {m.lender_name}
                        </span>
                        <span className="text-[#0E9F6E] text-sm" data-testid={`proc-fee-${m.rank}`}>
                          Proc fee: {m.proc_fee_purchase}%
                        </span>
                        {isCurrent && (
                          <span className="badge badge-teal text-xs">Current Lender</span>
                        )}
                      </div>
                      <p className="text-sm text-[#111827] mb-2" data-testid={`reason-${m.rank}`}>
                        {m.reason}
                      </p>
                      {m.watch_out && m.watch_out !== 'None' && (
                        <div className="flex items-start gap-2 mb-2" data-testid={`watch-out-${m.rank}`}>
                          <span className="text-base leading-none">⚠️</span>
                          <span className="text-sm text-[#92400E]">{m.watch_out}</span>
                        </div>
                      )}
                      <div className="text-xs text-[#6B7280]">
                        Avg processing: {m.avg_processing_days} days · Success rate: {m.broker_success_rate}%
                      </div>
                    </div>

                    {/* Select button */}
                    <div className="shrink-0">
                      <Button
                        onClick={() => selectLender(m.lender_id, m.lender_name)}
                        disabled={lenderSelected || selectingLenderId !== null}
                        className={`${
                          isCurrent
                            ? 'bg-[#D1D5DB] text-[#6B7280] cursor-default'
                            : lenderSelected
                            ? 'bg-[#E5E7EB] text-[#9CA3AF] cursor-not-allowed'
                            : 'bg-[#0E9F6E] hover:bg-[#0B8A5E] text-white'
                        }`}
                        data-testid={`select-lender-btn-${m.rank}`}
                      >
                        {selectingLenderId === m.lender_id
                          ? 'Selecting...'
                          : isCurrent
                          ? 'Selected'
                          : 'Select Lender'}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
