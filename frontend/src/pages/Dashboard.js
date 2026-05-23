import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { Skeleton } from '../components/ui/skeleton';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const formatCurrency = (value) => {
  if (!value) return '£0';
  return '£' + value.toLocaleString('en-GB');
};

const stageLabels = {
  new_enquiry: 'New Enquiry',
  fact_find: 'Fact Find',
  aip_submitted: 'AIP Submitted',
  aip_received: 'AIP Received',
  full_application: 'Full Application',
  valuation: 'Valuation',
  offer: 'Mortgage Offer',
  exchange: 'Exchange',
  completion: 'Completion',
  on_hold: 'On Hold',
  declined: 'Declined'
};

export function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const { data } = await axios.get(`${API}/dashboard/stats`, { withCredentials: true });
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const activePipelineStages = ['new_enquiry', 'fact_find', 'aip_submitted', 'aip_received', 'full_application', 'valuation', 'offer', 'exchange'];

  return (
    <div data-testid="dashboard-page">
      <div className="page-header">
        <h1>Dashboard</h1>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card" data-testid="stat-clients">
          <div className="stat-card-label">Total Clients</div>
          {loading ? (
            <Skeleton className="h-8 w-16" />
          ) : (
            <div className="stat-card-value">{stats?.clients_count || 0}</div>
          )}
        </div>

        <div className="stat-card" data-testid="stat-cases">
          <div className="stat-card-label">Active Cases</div>
          {loading ? (
            <Skeleton className="h-8 w-16" />
          ) : (
            <div className="stat-card-value">{stats?.cases_count || 0}</div>
          )}
        </div>

        <div className="stat-card" data-testid="stat-pending-commission">
          <div className="stat-card-label">Pending Commission</div>
          {loading ? (
            <Skeleton className="h-8 w-24" />
          ) : (
            <div className="stat-card-value">{formatCurrency(stats?.commissions?.pending)}</div>
          )}
        </div>

        <div className="stat-card" data-testid="stat-received-commission">
          <div className="stat-card-label">Received This Year</div>
          {loading ? (
            <Skeleton className="h-8 w-24" />
          ) : (
            <div className="stat-card-value">{formatCurrency(stats?.commissions?.received)}</div>
          )}
        </div>
      </div>

      {/* Commission Alerts */}
      {!loading && stats?.alerts && (
        stats.alerts.overdue_count > 0 ||
        stats.alerts.due_soon_count > 0 ||
        stats.alerts.clawback_risk_count > 0
      ) && (
        <div
          className="card mt-6 flex items-center flex-wrap gap-5 py-3"
          data-testid="commission-alerts-widget"
        >
          <span className="text-sm font-semibold text-[#111827]">Commission Alerts</span>
          {stats.alerts.overdue_count > 0 && (
            <a
              href="/commissions"
              className="flex items-center gap-1.5 text-sm text-[#EF4444] hover:underline"
              data-testid="alert-overdue"
            >
              <span className="w-2 h-2 rounded-full bg-[#EF4444] inline-block" />
              {stats.alerts.overdue_count} overdue
            </a>
          )}
          {stats.alerts.due_soon_count > 0 && (
            <a
              href="/commissions"
              className="flex items-center gap-1.5 text-sm text-[#F59E0B] hover:underline"
              data-testid="alert-due-soon"
            >
              <span className="w-2 h-2 rounded-full bg-[#F59E0B] inline-block" />
              {stats.alerts.due_soon_count} due this week
            </a>
          )}
          {stats.alerts.clawback_risk_count > 0 && (
            <a
              href="/commissions"
              className="flex items-center gap-1.5 text-sm text-[#D97706] hover:underline"
              data-testid="alert-clawback"
            >
              <span className="w-2 h-2 rounded-full bg-[#D97706] inline-block" />
              {stats.alerts.clawback_risk_count} clawback risk
            </a>
          )}
        </div>
      )}

      {/* Pipeline Overview */}
      <div className="card mt-6">
        <h2 className="text-lg font-semibold text-[#111827] mb-6">Pipeline Overview</h2>
        
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {activePipelineStages.map((stage) => {
              const count = stats?.pipeline?.[stage] || 0;
              const maxCount = Math.max(...activePipelineStages.map(s => stats?.pipeline?.[s] || 0), 1);
              const width = (count / maxCount) * 100;

              return (
                <div key={stage} className="flex items-center gap-4" data-testid={`pipeline-${stage}`}>
                  <div className="w-32 text-sm text-[#6B7280] truncate">
                    {stageLabels[stage]}
                  </div>
                  <div className="flex-1 bg-[#F3F4F6] rounded-full h-6 overflow-hidden">
                    <div
                      className="h-full bg-[#0E9F6E] rounded-full transition-all duration-500"
                      style={{ width: `${Math.max(width, count > 0 ? 5 : 0)}%` }}
                    />
                  </div>
                  <div className="w-8 text-sm font-medium text-[#111827] text-right">
                    {count}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Recent Cases */}
      {!loading && stats?.recent_cases?.length > 0 && (
        <div className="card mt-6" data-testid="recent-cases-section">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-[#111827]">Recent Cases</h2>
            <a href="/cases" className="text-sm text-[#0E9F6E] hover:underline">View all</a>
          </div>
          <table className="w-full">
            <thead>
              <tr className="table-header">
                <th className="text-left px-4 py-2 text-xs">Client</th>
                <th className="text-left px-4 py-2 text-xs">Stage</th>
                <th className="text-left px-4 py-2 text-xs">Lender</th>
                <th className="text-right px-4 py-2 text-xs">Loan Amount</th>
              </tr>
            </thead>
            <tbody>
              {stats.recent_cases.map((c) => (
                <tr key={c.id} className="table-row" data-testid={`recent-case-${c.id}`}>
                  <td className="px-4 py-2 text-sm font-medium text-[#111827]">{c.client_name}</td>
                  <td className="px-4 py-2">
                    <span className="badge badge-blue text-xs">{stageLabels[c.stage] || c.stage}</span>
                  </td>
                  <td className="px-4 py-2 text-sm text-[#6B7280]">{c.lender_name}</td>
                  <td className="px-4 py-2 text-sm text-[#111827] text-right">{formatCurrency(c.loan_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        <a
          href="/clients"
          className="card hover:border-[#0E9F6E] transition-colors"
          data-testid="quick-action-clients"
        >
          <h3 className="font-semibold text-[#111827] mb-2">Manage Clients</h3>
          <p className="text-sm text-[#6B7280]">Add, edit, and view your client database</p>
        </a>

        <a
          href="/pipeline"
          className="card hover:border-[#0E9F6E] transition-colors"
          data-testid="quick-action-pipeline"
        >
          <h3 className="font-semibold text-[#111827] mb-2">View Pipeline</h3>
          <p className="text-sm text-[#6B7280]">Track cases through stages with Kanban view</p>
        </a>

        <a
          href="/commissions"
          className="card hover:border-[#0E9F6E] transition-colors"
          data-testid="quick-action-commissions"
        >
          <h3 className="font-semibold text-[#111827] mb-2">Track Commissions</h3>
          <p className="text-sm text-[#6B7280]">Monitor expected and received payments</p>
        </a>
      </div>
    </div>
  );
}
