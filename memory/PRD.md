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
- API Base URL: https://broker-dash-9.preview.emergentagent.com/api
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

## Next Tasks (Open Backlog)
1. Set up EMERGENT_LLM_KEY for document storage (P1)
2. Email notifications for commission due dates (P1)
3. Make invoice sequence atomic (use findOneAndUpdate with $inc + upsert to avoid race conditions in concurrent invoice generation)
4. Server-side search on Commissions & Pipeline (currently client-side, only filters current page of paginated results)
5. Reduce N+1 queries in /api/commissions/reminders via $lookup or batched $in queries
6. Phase 2 AI features (lender matching, OCR auto-fill, rate comparison)

