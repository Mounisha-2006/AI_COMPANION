import React from 'react';
import { Navigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function AdminRoute({ children }) {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center' }}>
        <div className="spinner" style={{ width: 32, height: 32, color: 'var(--primary)' }}></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const isAdmin = user?.role && user.role.toUpperCase() === 'ADMIN';

  if (!isAdmin) {
    return (
      <div style={{ padding: 40, maxWidth: 600, margin: '60px auto', textAlign: 'center' }}>
        <div style={{ fontSize: 64, marginBottom: 16 }}>🛡️🚫</div>
        <h2 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-main)', marginBottom: 8 }}>
          403 - Forbidden: Admin Access Required
        </h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: 24, lineHeight: 1.6 }}>
          Your current account (<strong>{user?.email}</strong>) has the role <code>{user?.role || 'user'}</code>.
          Access to the Admin Console is strictly restricted to platform administrators.
        </p>
        <Link to="/dashboard" className="btn btn-primary">
          Return to Student Dashboard
        </Link>
      </div>
    );
  }

  return children;
}
