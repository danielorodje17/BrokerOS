# BrokerOS - Product Requirements Document

## Original Problem Statement
BrokerOS is a web-based SaaS application for independent mortgage brokers in the UK. Phase 1 MVP includes:
1. Authentication & user profile
2. Client & Case Management (CRM)
3. Deal Pipeline Tracker (Kanban board)
4. Lender Panel Manager
5. Commission Tracker

## Tech Stack
- Frontend: React 18 with JavaScript, Tailwind CSS
- Backend: FastAPI (Python)
- Database: MongoDB
- File Storage: Emergent Object Storage (requires EMERGENT_LLM_KEY)
- Authentication: JWT with refresh tokens, bcrypt, httpOnly cookies

## User Personas
- **Independent Mortgage Broker**: Primary user - manages clients, cases, lenders, and commissions
- **Admin**: Full access to all features plus user management capabilities

## Core Requirements (Static)
- Clean, professional UI following UK financial services standards
- GDPR-compliant client data handling with consent tracking
- LTV auto-calculation (loan_amount / property_value * 100)
- Commission tracking with clawback risk monitoring
- Kanban pipeline for case progress visualization

## What's Been Implemented (23 May 2026)

### Authentication Module
- [x] JWT login with httpOnly cookies
- [x] User registration with onboarding wizard
- [x] Forgot password flow
- [x] Profile settings with password change
- [x] Admin seeding on startup
- [x] Brute force protection (5 attempts, 15 min lockout)

### Client Management
- [x] Full CRUD operations
- [x] Client search
- [x] Employment type tracking
- [x] Credit profile (clean/minor_issues/adverse)
- [x] Annual income tracking
- [x] GDPR consent date

### Case Management
- [x] Full CRUD operations
- [x] Link to client and lender
- [x] Mortgage type (residential/btl/remortgage/product_transfer/bridging)
- [x] Stage tracking (11 stages from new_enquiry to completion)
- [x] Auto LTV calculation
- [x] Rate type and percentage
- [x] **Case Detail Page** with comprehensive view of case, client, and lender info
- [x] **Case Notes Timeline** - immutable notes with author name, relative timestamps, 2000 char limit

### Pipeline (Kanban)
- [x] Visual Kanban board by stage
- [x] Click card to view/update stage
- [x] Stage summary cards (Completed, On Hold, Declined)

### Lender Panel
- [x] Full CRUD operations
- [x] BDM contact details
- [x] Proc fee percentages (purchase/remortgage/btl)
- [x] Lending criteria (min/max loan, max LTV, min income)
- [x] Accepts flags (self-employed, contractors, adverse)
- [x] Performance metrics (avg processing days, success rate)

### Commission Tracker
- [x] Full CRUD linked to cases
- [x] Expected vs received amounts
- [x] Status tracking (pending/invoiced/received/overdue/clawback_risk)
- [x] Clawback risk date
- [x] Summary cards (pending total, received total)
- [x] **PDF Invoice Generation** - professional invoices with INV-YYYY-NNNN format

### Dashboard
- [x] Stats cards (clients, cases, pending commission, received)
- [x] Pipeline overview with progress bars
- [x] Quick action cards

## Prioritized Backlog

### P0 (Critical) - All Complete
All P0 features delivered in MVP.

### P1 (High Priority)
- [ ] Document upload/download (requires EMERGENT_LLM_KEY setup)
- [x] ~~Notes per case with timeline~~ ✓ Implemented
- [ ] Case search by client name
- [ ] Email notifications for commission due dates

### P2 (Medium Priority)
- [ ] Multi-tenancy (team management)
- [ ] Reporting dashboard
- [ ] Export to CSV/PDF
- [ ] Calendar integration for appointments
- [ ] Mobile responsive improvements

### P3 (Future/AI Phase 2)
- [ ] AI-powered lender matching
- [ ] Document OCR and auto-fill
- [ ] Compliance checklist automation
- [ ] Rate comparison engine

## Test Credentials
- Admin: admin@brokeros.com / Admin123!
- API Base URL: https://daily-broker-brief.preview.emergentagent.com/api
- Test Case ID: 09ecdc6c-828e-4134-b316-9c112ccd2848

## New Features (Phase 1 Extension)

### Case Notes Timeline
- **Endpoint**: POST /api/notes, GET /api/notes?case_id={id}
- **Features**: Immutable notes, author_name denormalized, 2000 char limit, sorted desc by created_at
- **UI**: Textarea with character counter (X/2000), navy Add Note button, note cards with teal author and grey relative time

### PDF Invoice Generation
- **Endpoint**: GET /api/commissions/{id}/invoice
- **Invoice Format**: INV-YYYY-NNNN (sequential per broker per year)
- **Collection**: invoice_sequences (user_id, year, last_number)
- **PDF Library**: reportlab
- **Content**: Broker info (name, FCA number), Lender, Client, Case reference, Loan amount, Commission amount, 30-day payment terms
- **Persistence**: invoice_number now persisted on commission_records on PDF download (so it can be searched)

### Commission Due-Date Reminders (Extension 3 — 23 May 2026)
- **Endpoint**: GET /api/commissions/reminders → {success, data:{due_soon[], overdue[]}}
- **due_soon**: non-received commissions with expected_payment_date within next 14 days (sorted asc by days_until_due)
- **overdue**: non-received commissions with expected_payment_date >30 days in the past (sorted asc by days_overdue)
- **UI**: Yellow (#FEF3C7/#F59E0B) "Due Soon" panel + Red (#FEF2F2/#EF4444) "Overdue" panel above filters; dismiss button; each reminder is clickable → scrolls to row and applies bg-yellow-100 flash for 2s

### Search Improvements (Extension 4 — 23 May 2026)
- **Pipeline.js**: Added Kanban/List view toggle. Search bar visible ONLY in List view; client-side, real-time, case-insensitive; matches client first/last/full name and lender name. Empty-state with "Clear search" button.
- **Commissions.js**: Search now matches client name, lender name, AND invoice_number (INV-YYYY-NNNN). Placeholder updated to "Search by client, lender or invoice #...".

### Atomic Invoice Sequence (23 May 2026)
- Replaced multi-step find/insert/update with atomic `find_one_and_update($inc, upsert=True)` via `pymongo.ReturnDocument.AFTER`
- Year-rollover handled by preceding `update_one($set: {last_number: 0})` when year field mismatches, then the increment gives 1
- No change to INV-YYYY-NNNN format or existing data

### Dashboard Commission Alerts Widget (23 May 2026)
- Compact bar below stats grid: shows red dot (overdue), amber dot (due this week, 14-day window), amber dot (clawback risk active)
- Each alert is a clickable link to `/commissions`; entire widget hidden when all counts are zero
- Counts computed in `/api/dashboard/stats` alongside existing pipeline/commission data

### Dashboard Recent Cases Table (23 May 2026)
- Shows 5 most recently created cases: Client name, Stage badge, Lender, Loan Amount
- `View all` link navigates to `/cases`
- Backend: enriched with client/lender info via per-case lookups in `dashboard.py`

### Extension 6: Clawback Risk Tab (23 May 2026)
- New `Clawback Risk` tab on Commission Tracker page (amber/orange indicator)
- Backend: `GET /api/commissions/clawback-risk` — returns commissions where `clawback_risk_until > today`, sorted by date asc, enriched with client/lender/days_remaining
- Days Remaining colour-coded: red ≤30, amber ≤90, green >90
- Count badge on tab when items exist; empty state message when none
- All existing CRUD unaffected; clawback list refreshes on commission add/edit/delete

### Extension 7: Team Permission Layer (23 May 2026)
- **`routes/deps.py`**: Added `get_case_filter(user)` — returns `{"assigned_broker_id": user.id}` for advisers, `{}` for all others
- **`routes/cases.py`**: All 5 endpoints use `_check_adviser_access` helper; `list_cases` uses `get_case_filter` merged with other filters; admin/principal see all cases unrestricted
- **`routes/commissions.py`**: List endpoint — advisers filtered by their case IDs; principal/admin query `{}` (see all commissions)
- **`routes/notes.py`**: Both note list endpoints check adviser case ownership; principals/admins pass freely
- **`routes/auth.py`**: `GET /api/auth/team/members` — returns 403 for adviser, `{success:true, data:[]}` when no team_id, or full team list by team_id
- **Sidebar.js**: Role label now handles admin → "Administrator" / principal → "Principal" / adviser → "Adviser"
- **Pipeline.js / Clients.js / Commissions.js**: Broker filter dropdown (leftmost, `All Brokers` default) — fetched from `/auth/team/members` on mount for principal/admin; hidden when empty or adviser; client-side filter on `assigned_broker_id` / `user_id`
- **`scripts/migrate_assign_cases.py`**: Idempotent migration assigns orphaned cases to first admin
- Tested: 31/31 backend + 100% frontend ✅

## Phase 2 - AI Features

### AI Feature 1: Borrower Strength Score (23 May 2026)
- **Endpoint**: `POST /api/ai/borrower-score` body `{client_id}` → `{success, data:{score, classification, colour, summary, breakdown}}`
- **Score model** (deterministic, 0-100):
  - Employment (max 30): employed=30, contractor=22, self_employed=18, retired=15, other=10
  - Income (max 25): >£75k=25, £50-75k=20, £35-50k=15, £20-35k=10, <£20k=5
  - Credit (max 30): clean=30, minor_issues=18, adverse=5
  - GDPR consent (max 10): yes=10, no=0
  - Documents (max 5): ≥1 file=5, else=0
- **Classification**: ≥80=Strong(green), ≥60=Good(teal), ≥40=Fair(amber), <40=Weak(red)
- **AI summary**: Claude `claude-sonnet-4-5` via `emergentintegrations.LlmChat` with `EMERGENT_LLM_KEY`. 2-3 sentence plain-English broker brief. Graceful degradation on Claude failure.
- **UI**: Borrower Strength Score card on `CaseDetail.js` below Client Details — large coloured score, classification badge, horizontal progress bar, AI summary panel, 5 breakdown rows, Recalculate button. Auto-loads on page mount via `client.id` from case.
- **Files**: `routes/ai.py`, `routes/__init__.py`, `server.py` (ai_router registered), `frontend/src/pages/CaseDetail.js`
- **Tested**: 13/13 backend pytest + 100% frontend (iteration_7.json)

### AI Feature 2: Lender Matching Engine (23 May 2026)
- **Endpoint**: `POST /api/ai/lender-match` body `{case_id}` → `{success, data:{matches[], eligible_count, total_lenders, message}}`
- **Hard filter** (deterministic, pre-Claude): excludes lenders where max_ltv<case.ltv, min/max_loan out of range, employment/credit incompatible (self_employed, contractor, adverse)
- **Claude ranking**: `claude-sonnet-4-5` returns JSON array with rank, reason, watch_out per lender; merged with full lender data and re-numbered
- **Fallback**: on Claude failure → eligible lenders sorted by proc_fee_purchase desc with reason="AI ranking unavailable"
- **Lender selection**: `PATCH /api/cases/{case_id}/lender?lender_id=X` validates lender ownership, updates case, returns enriched case
- **UI**: New "AI Lender Match" tab on CaseDetail; Find Best Lenders button → loading spinner → vertical ranked cards (navy rank badge, bold name, teal proc fee, AI reason, amber ⚠️ watch_out, processing/success metrics, Select Lender button). Current lender highlighted with teal left border + "Current Lender" badge. Empty state when no matches.
- **Files**: `routes/ai.py` (+lender-match), `routes/cases.py` (+PATCH /lender), `frontend/src/pages/CaseDetail.js` (tabs + match UI)
- **Tested**: 14/14 backend + 100% frontend (iteration_8.json)

### AI Feature 3: Daily Briefing (23 May 2026)
- **Endpoints**:
  - `GET /api/ai/daily-briefing` → `{briefing, generated_at, cached}` — generates via Claude on first call of the day, returns cached version on subsequent calls
  - `GET /api/ai/daily-briefing?probe=true` → returns cached briefing if present, else `{briefing:null, cached:false}` WITHOUT calling Claude (fast page-load probe)
  - `DELETE /api/ai/daily-briefing` → clears today's cache (used by Regenerate)
- **Context**: active cases (stage+days-in-stage+lender+client), commission alerts (overdue + due-this-week counts & totals), clawback risk within 60 days
- **Model**: `claude-sonnet-4-5` via `emergentintegrations`. British English. Plain-text output (no markdown).
- **Cache**: `daily_briefings` collection keyed by `{user_id, date(YYYY-MM-DD)}` with upsert
- **UI**: Top of Dashboard, teal 4px left border on light grey card. Probe on mount; if cached → renders paragraphs + "Regenerate" link; else → "Generate Briefing" button. Loading state: spinner + "Claude is reviewing your pipeline…"
- **Files**: `routes/ai.py` (+daily-briefing GET/DELETE), `frontend/src/pages/Dashboard.js`
- **Tested**: 13/13 backend + 13/13 frontend (iteration_9.json)

## Next Tasks (Open Backlog)
1. Document storage with Emergent Object Storage (P1)
2. Email notifications for commission due dates (P1)
3. Phase 2 AI Features 2, 3, 4 (awaiting specs from user) (P1)
4. Team management UI — invite advisers, assign team_id, set roles (P1)
5. Server-side search on Commissions & Pipeline (currently client-side, filters current page only)
6. Reduce N+1 queries in reminders/clawback/cases list endpoints via $lookup
7. Commission reminders/clawback-risk to respect team scope for admins (currently personal view)
8. Borrower Score: cache result per client_id with manual invalidation on Recalculate (avoid LLM call on every recalculate)
9. Refactor CaseDetail.js — extract BorrowerScoreCard and NotesTimeline into separate components (~510 lines)

