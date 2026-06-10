import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const navItems = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/clients', label: 'Clients' },
  { path: '/cases', label: 'Cases' },
  { path: '/pipeline', label: 'Pipeline' },
  { path: '/lenders', label: 'Lenders' },
  { path: '/commissions', label: 'Commissions' },
  { path: '/retention', label: 'Retention', badge: true },
  { path: '/settings', label: 'Settings' },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [retentionCount, setRetentionCount] = useState(0);

  useEffect(() => {
    if (!user) return;
    axios.get(`${API}/retention/cases?window=90`, { withCredentials: true })
      .then(({ data }) => {
        const s = data.data?.summary;
        if (s) setRetentionCount((s.expiring_90_days || 0) + (s.already_expired || 0));
      })
      .catch(() => {});
  }, [user]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const getInitials = () => {
    if (!user) return '?';
    const first = user.first_name?.[0] || '';
    const last = user.last_name?.[0] || '';
    return (first + last).toUpperCase() || user.email?.[0]?.toUpperCase() || '?';
  };

  const getUserName = () => {
    if (!user) return '';
    if (user.first_name || user.last_name) {
      return `${user.first_name || ''} ${user.last_name || ''}`.trim();
    }
    return user.email;
  };

  return (
    <aside className="sidebar" data-testid="sidebar">
      <div className="sidebar-logo">
        <h1>BrokerOS</h1>
        <p>Practice Management</p>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? 'active' : ''}`
            }
            data-testid={`nav-${item.label.toLowerCase()}`}
          >
            <span className="flex-1">{item.label}</span>
            {item.badge && retentionCount > 0 && (
              <span
                style={{
                  background: '#EF4444',
                  color: 'white',
                  fontSize: '11px',
                  fontWeight: 700,
                  padding: '1px 6px',
                  borderRadius: '9999px',
                  minWidth: '18px',
                  textAlign: 'center',
                  lineHeight: '16px',
                }}
                data-testid="retention-badge"
              >
                {retentionCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-avatar" data-testid="user-avatar">
            {getInitials()}
          </div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name" data-testid="user-name">
              {getUserName()}
            </div>
            <div className="sidebar-user-role" data-testid="user-role">
              {user?.role === 'admin'
                ? 'Administrator'
                : user?.role === 'principal'
                ? 'Principal'
                : 'Adviser'}
            </div>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="sidebar-logout"
          data-testid="logout-btn"
        >
          Log out
        </button>
      </div>
    </aside>
  );
}
