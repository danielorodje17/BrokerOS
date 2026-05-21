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

## What's Been Implemented (21 Jan 2026)

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

### Dashboard
- [x] Stats cards (clients, cases, pending commission, received)
- [x] Pipeline overview with progress bars
- [x] Quick action cards

## Prioritized Backlog

### P0 (Critical) - All Complete
All P0 features delivered in MVP.

### P1 (High Priority)
- [ ] Document upload/download (requires EMERGENT_LLM_KEY setup)
- [ ] Notes per case with timeline
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
- API Base URL: https://commission-track-28.preview.emergentagent.com/api

## Next Tasks
1. Set up EMERGENT_LLM_KEY for document storage
2. Implement case notes timeline
3. Extend case search to include client name
4. Add email notifications for commission tracking
