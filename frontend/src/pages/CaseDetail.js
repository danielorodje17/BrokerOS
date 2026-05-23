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

export function CaseDetail() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState(null);
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notesLoading, setNotesLoading] = useState(true);
  const [noteContent, setNoteContent] = useState('');
  const [addingNote, setAddingNote] = useState(false);

  const fetchCase = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/cases/${caseId}`, { withCredentials: true });
      setCaseData(data);
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
      setNotes(data.notes);
    } catch (error) {
      console.error('Failed to load notes:', error);
    } finally {
      setNotesLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchCase();
    fetchNotes();
  }, [fetchCase, fetchNotes]);

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
            <div className="absolute bottom-3 right-3 text-xs text-[#6B7280]" data-testid="note-char-count">
              {noteContent.length} / 2000
            </div>
          </div>
          <div className="flex justify-end mt-3">
            <Button
              onClick={handleAddNote}
              disabled={!noteContent.trim() || addingNote}
              className="bg-[#0A2342] hover:bg-[#0d2d52] text-white"
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
    </div>
  );
}
