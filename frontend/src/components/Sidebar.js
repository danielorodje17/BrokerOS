import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const navItems = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/clients', label: 'Clients' },
  { path: '/cases', label: 'Cases' },
  { path: '/pipeline', label: 'Pipeline' },
  { path: '/lenders', label: 'Lenders' },
  { path: '/commissions', label: 'Commissions' },
  { path: '/settings', label: 'Settings' },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

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
            {item.label}
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
            <div className="sidebar-user-role">
              {user?.role === 'admin' ? 'Administrator' : 'Adviser'}
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
