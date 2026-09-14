import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-icon">📚</div>
        <div>
          <div className="brand-title">AI Study</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Companion</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to="/dashboard"
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <span>📊</span> Dashboard
        </NavLink>
        <NavLink
          to="/spaces"
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <span>📁</span> Study Spaces
        </NavLink>
        <NavLink
          to="/analytics"
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <span>📈</span> Analytics
        </NavLink>
        {user?.role?.toUpperCase() === 'ADMIN' && (
          <NavLink
            to="/admin"
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            style={{ marginTop: 8, borderLeft: '3px solid #f59e0b', background: 'rgba(245, 158, 11, 0.08)' }}
          >
            <span>🛡️</span> Admin Console
          </NavLink>
        )}
      </nav>

      <div className="sidebar-footer">
        <div className="user-badge">
          <span className="user-name">{user?.name || 'Student'}</span>
          <span className="user-role">{user?.role || 'user'}</span>
        </div>
        <button
          onClick={handleLogout}
          className="btn btn-secondary btn-sm"
          title="Sign out"
          style={{ padding: '4px 8px' }}
        >
          Logout
        </button>
      </div>
    </aside>
  );
}
