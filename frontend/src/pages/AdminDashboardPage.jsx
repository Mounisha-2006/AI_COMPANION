import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { EmptyState } from '../components/EmptyState';

export function AdminDashboardPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Overview data
  const [overview, setOverview] = useState(null);

  // Users data & Inspection
  const [usersList, setUsersList] = useState([]);
  const [userSearch, setUserSearch] = useState('');
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [inspectedUser, setInspectedUser] = useState(null);
  const [isInspecting, setIsInspecting] = useState(false);

  // AI Usage data
  const [aiUsage, setAiUsage] = useState(null);

  // AI Evaluation data
  const [aiEvaluation, setAiEvaluation] = useState(null);
  const [isRunningEvaluation, setIsRunningEvaluation] = useState(false);

  // System Health data
  const [systemHealth, setSystemHealth] = useState(null);

  const fetchOverview = async () => {
    try {
      const data = await api.admin.getOverview();
      setOverview(data);
    } catch (err) {
      console.error('Failed to load admin overview:', err);
      setError(err.message || 'Failed to load platform overview.');
    }
  };

  const fetchUsers = async (search = '') => {
    try {
      const data = await api.admin.listUsers(100, 0, search || null);
      setUsersList(data);
    } catch (err) {
      console.error('Failed to load users:', err);
      setError(err.message || 'Failed to load user directory.');
    }
  };

  const handleInspectUser = async (userId) => {
    setIsInspecting(true);
    setSelectedUserId(userId);
    try {
      const data = await api.admin.inspectUser(userId);
      setInspectedUser(data);
    } catch (err) {
      console.error('Failed to inspect user:', err);
      setError(err.message || 'Failed to inspect user details.');
    } finally {
      setIsInspecting(false);
    }
  };

  const fetchAIUsage = async () => {
    try {
      const data = await api.admin.getAIUsage(100);
      setAiUsage(data);
    } catch (err) {
      console.error('Failed to load AI usage:', err);
      setError(err.message || 'Failed to load AI usage metrics.');
    }
  };

  const fetchAIEvaluation = async () => {
    try {
      const data = await api.admin.getAIEvaluation();
      setAiEvaluation(data);
    } catch (err) {
      console.error('Failed to load AI evaluation:', err);
      setError(err.message || 'Failed to load AI evaluation benchmarks.');
    }
  };

  const handleRunEvaluation = async () => {
    setIsRunningEvaluation(true);
    try {
      const data = await api.admin.runAIEvaluation();
      setAiEvaluation(data);
    } catch (err) {
      console.error('Failed to run AI evaluation:', err);
      setError(err.message || 'Failed to execute evaluation test suite.');
    } finally {
      setIsRunningEvaluation(false);
    }
  };

  const fetchSystemHealth = async () => {
    try {
      const data = await api.admin.getSystemHealth();
      setSystemHealth(data);
    } catch (err) {
      console.error('Failed to load system health:', err);
      setError(err.message || 'Failed to retrieve system health metrics.');
    }
  };

  const loadDataForTab = async (tab) => {
    setIsLoading(true);
    setError('');
    try {
      if (tab === 'overview') await fetchOverview();
      else if (tab === 'users') await fetchUsers(userSearch);
      else if (tab === 'ai-usage') await fetchAIUsage();
      else if (tab === 'evaluation') await fetchAIEvaluation();
      else if (tab === 'health') await fetchSystemHealth();
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDataForTab(activeTab);
  }, [activeTab]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchUsers(userSearch);
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="admin-page" style={{ padding: '24px 32px', maxWidth: 1400, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 28 }}>🛡️</span>
            <h1 style={{ fontSize: 26, fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
              Admin Console
            </h1>
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                textTransform: 'uppercase',
                padding: '3px 8px',
                borderRadius: 4,
                backgroundColor: '#f59e0b',
                color: '#fff',
                letterSpacing: 0.5,
              }}
            >
              ADMIN
            </span>
          </div>
          <p style={{ color: 'var(--text-muted)', margin: '6px 0 0 0', fontSize: 14 }}>
            Platform Overview, User Inspection, AI Usage & Lightweight System Diagnostics
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={() => loadDataForTab(activeTab)}
            className="btn btn-secondary btn-sm"
            disabled={isLoading}
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
          >
            🔄 Refresh Data
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div
        style={{
          display: 'flex',
          gap: 8,
          borderBottom: '1px solid var(--border-color)',
          marginBottom: 24,
        }}
      >
        {[
          { id: 'overview', label: '📊 Platform Overview' },
          { id: 'users', label: '👥 Users & Inspection' },
          { id: 'ai-usage', label: '⚡ AI Usage & Costs' },
          { id: 'evaluation', label: '🧪 AI Evaluation & Benchmarks' },
          { id: 'health', label: '🩺 System Health' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              setActiveTab(tab.id);
              if (tab.id === 'users') {
                setSelectedUserId(null);
                setInspectedUser(null);
              }
            }}
            style={{
              padding: '10px 18px',
              fontWeight: 600,
              fontSize: 14,
              border: 'none',
              backgroundColor: 'transparent',
              cursor: 'pointer',
              color: activeTab === tab.id ? 'var(--primary)' : 'var(--text-muted)',
              borderBottom: activeTab === tab.id ? '3px solid var(--primary)' : '3px solid transparent',
              transition: 'all 0.2s',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error alert */}
      {error && (
        <div
          style={{
            padding: 12,
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid #ef4444',
            borderRadius: 6,
            color: '#ef4444',
            marginBottom: 20,
            fontSize: 14,
          }}
        >
          {error}
        </div>
      )}

      {/* Loading indicator */}
      {isLoading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
          <div className="spinner" style={{ width: 32, height: 32, color: 'var(--primary)' }}></div>
        </div>
      )}

      {/* TAB 1: OVERVIEW */}
      {!isLoading && activeTab === 'overview' && overview && (
        <div>
          {/* KPI Cards */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
              gap: 16,
              marginBottom: 28,
            }}
          >
            {[
              { label: 'Total Users', value: overview.kpis.total_users, icon: '👥', color: '#3b82f6' },
              { label: 'Total Spaces', value: overview.kpis.total_spaces, icon: '📁', color: '#8b5cf6' },
              { label: 'Total Projects', value: overview.kpis.total_projects, icon: '📂', color: '#10b981' },
              { label: 'Total Materials', value: overview.kpis.total_materials, icon: '📄', color: '#f59e0b' },
              { label: 'Tutor Interactions', value: overview.kpis.total_tutor_interactions, icon: '🤖', color: '#06b6d4' },
              { label: 'Total Quizzes', value: overview.kpis.total_quizzes, icon: '📝', color: '#ec4899' },
              { label: 'Total Assessments', value: overview.kpis.total_assessments, icon: '🎯', color: '#6366f1' },
            ].map((kpi, idx) => (
              <div
                key={idx}
                className="card"
                style={{
                  padding: 16,
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: 8,
                  border: '1px solid var(--border-color)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{kpi.label}</span>
                  <span style={{ fontSize: 18 }}>{kpi.icon}</span>
                </div>
                <div style={{ fontSize: 24, fontWeight: 700, color: kpi.color, marginTop: 8 }}>
                  {kpi.value.toLocaleString()}
                </div>
              </div>
            ))}
          </div>

          {/* Activity Feeds */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 28 }}>
            {/* Recent Users */}
            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 18,
              }}
            >
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 14px 0', color: 'var(--text-main)' }}>
                👥 Recent Users
              </h3>
              {overview.recent_users && overview.recent_users.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {overview.recent_users.map((u) => (
                    <div
                      key={u.id}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '10px 12px',
                        borderRadius: 6,
                        backgroundColor: 'var(--bg-main)',
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 14 }}>{u.name}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{u.email}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <span
                          style={{
                            fontSize: 11,
                            padding: '2px 6px',
                            borderRadius: 4,
                            backgroundColor: u.role === 'ADMIN' ? '#f59e0b' : '#3b82f6',
                            color: '#fff',
                            fontWeight: 600,
                          }}
                        >
                          {u.role}
                        </span>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                          {u.spaces_count} spaces · {u.projects_count} projects
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title="No recent users" />
              )}
            </div>

            {/* Recent Projects */}
            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 18,
              }}
            >
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 14px 0', color: 'var(--text-main)' }}>
                📂 Recent Projects
              </h3>
              {overview.recent_projects && overview.recent_projects.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {overview.recent_projects.map((p) => (
                    <div
                      key={p.id}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '10px 12px',
                        borderRadius: 6,
                        backgroundColor: 'var(--bg-main)',
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 14 }}>{p.name}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                          Space: {p.space_name} · Owner: {p.user_email}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <span style={{ fontSize: 12, fontWeight: 600 }}>{p.materials_count} files</span>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                          {formatTime(p.created_at)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title="No recent projects" />
              )}
            </div>
          </div>

          {/* Activity Feeds Row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            {/* Recent Activity Events */}
            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 18,
              }}
            >
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 14px 0', color: 'var(--text-main)' }}>
                ⚡ Platform Activity Stream
              </h3>
              {overview.recent_activity_events && overview.recent_activity_events.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 350, overflowY: 'auto' }}>
                  {overview.recent_activity_events.map((ev) => (
                    <div
                      key={ev.id}
                      style={{
                        padding: '8px 10px',
                        borderRadius: 6,
                        backgroundColor: 'var(--bg-main)',
                        fontSize: 13,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <div>
                        <span style={{ fontWeight: 600, color: 'var(--primary)' }}>{ev.event_type}</span>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>User ID: {ev.user_id}</div>
                      </div>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{formatTime(ev.created_at)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title="No activity recorded" />
              )}
            </div>

            {/* Recent Material Processing Events */}
            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 18,
              }}
            >
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 14px 0', color: 'var(--text-main)' }}>
                📄 Material Processing Feed
              </h3>
              {overview.recent_material_events && overview.recent_material_events.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 350, overflowY: 'auto' }}>
                  {overview.recent_material_events.map((ev) => (
                    <div
                      key={ev.id}
                      style={{
                        padding: '8px 10px',
                        borderRadius: 6,
                        backgroundColor: 'var(--bg-main)',
                        fontSize: 13,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <div>
                        <span
                          style={{
                            fontWeight: 600,
                            color: ev.event_type.includes('FAILED') ? '#ef4444' : '#10b981',
                          }}
                        >
                          {ev.event_type}
                        </span>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                          File: {ev.metadata?.filename || 'Document'} · Project: {ev.project_id || 'N/A'}
                        </div>
                      </div>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{formatTime(ev.created_at)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title="No material events recorded" />
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: USERS & INSPECTION */}
      {!isLoading && activeTab === 'users' && (
        <div>
          {!inspectedUser ? (
            <div>
              {/* Search Bar */}
              <form
                onSubmit={handleSearchSubmit}
                style={{ display: 'flex', gap: 12, marginBottom: 20, maxWidth: 500 }}
              >
                <input
                  type="text"
                  placeholder="Search users by name or email..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  style={{
                    flex: 1,
                    padding: '8px 14px',
                    borderRadius: 6,
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-card)',
                    color: 'var(--text-main)',
                    fontSize: 14,
                  }}
                />
                <button type="submit" className="btn btn-primary btn-sm">
                  Search
                </button>
                {userSearch && (
                  <button
                    type="button"
                    onClick={() => {
                      setUserSearch('');
                      fetchUsers('');
                    }}
                    className="btn btn-secondary btn-sm"
                  >
                    Clear
                  </button>
                )}
              </form>

              {/* Users Directory Table */}
              <div
                className="card"
                style={{
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: 8,
                  border: '1px solid var(--border-color)',
                  overflow: 'hidden',
                }}
              >
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 14 }}>
                  <thead>
                    <tr
                      style={{
                        backgroundColor: 'var(--bg-main)',
                        borderBottom: '1px solid var(--border-color)',
                      }}
                    >
                      <th style={{ padding: '12px 16px' }}>User</th>
                      <th style={{ padding: '12px 16px' }}>Role</th>
                      <th style={{ padding: '12px 16px' }}>Spaces</th>
                      <th style={{ padding: '12px 16px' }}>Projects</th>
                      <th style={{ padding: '12px 16px' }}>Quizzes</th>
                      <th style={{ padding: '12px 16px' }}>Tutor Queries</th>
                      <th style={{ padding: '12px 16px' }}>Mastery</th>
                      <th style={{ padding: '12px 16px' }}>Joined</th>
                      <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usersList.map((u) => (
                      <tr
                        key={u.id}
                        style={{
                          borderBottom: '1px solid var(--border-color)',
                        }}
                      >
                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ fontWeight: 600 }}>{u.name}</div>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{u.email}</div>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <span
                            style={{
                              fontSize: 11,
                              padding: '2px 6px',
                              borderRadius: 4,
                              backgroundColor: u.role === 'ADMIN' ? '#f59e0b' : '#3b82f6',
                              color: '#fff',
                              fontWeight: 600,
                            }}
                          >
                            {u.role}
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px' }}>{u.spaces_count}</td>
                        <td style={{ padding: '12px 16px' }}>{u.projects_count}</td>
                        <td style={{ padding: '12px 16px' }}>{u.quizzes_count}</td>
                        <td style={{ padding: '12px 16px' }}>{u.tutor_questions_count}</td>
                        <td style={{ padding: '12px 16px' }}>
                          <span style={{ fontWeight: 600, color: 'var(--primary)' }}>
                            {u.overall_mastery}%
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-muted)' }}>
                          {formatTime(u.created_at)}
                        </td>
                        <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                          <button
                            onClick={() => handleInspectUser(u.id)}
                            className="btn btn-secondary btn-sm"
                            disabled={isInspecting && selectedUserId === u.id}
                          >
                            👁️ Inspect
                          </button>
                        </td>
                      </tr>
                    ))}
                    {usersList.length === 0 && (
                      <tr>
                        <td colSpan={9} style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>
                          No users found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            /* USER INSPECT VIEW */
            <div>
              {/* Observation Notice & Back button */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: 16,
                }}
              >
                <button
                  onClick={() => {
                    setInspectedUser(null);
                    setSelectedUserId(null);
                  }}
                  className="btn btn-secondary btn-sm"
                >
                  ⬅️ Back to All Users
                </button>
                <div
                  style={{
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    border: '1px solid #f59e0b',
                    borderRadius: 6,
                    padding: '6px 12px',
                    fontSize: 13,
                    color: '#d97706',
                    fontWeight: 600,
                  }}
                >
                  👁️ Observation-Only Mode: Administrator view is read-only. Modifying user data is disabled.
                </div>
              </div>

              {/* User Profile Card */}
              <div
                className="card"
                style={{
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: 8,
                  border: '1px solid var(--border-color)',
                  padding: 20,
                  marginBottom: 20,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>
                      {inspectedUser.user.name}
                    </h2>
                    <div style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
                      {inspectedUser.user.email} · User ID: {inspectedUser.user.id} · Joined: {formatTime(inspectedUser.user.created_at)}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 16, textAlign: 'center' }}>
                    <div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Overall Mastery</div>
                      <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--primary)' }}>
                        {inspectedUser.user.overall_mastery}%
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Quiz Accuracy</div>
                      <div style={{ fontSize: 20, fontWeight: 700, color: '#10b981' }}>
                        {inspectedUser.quiz_accuracy}%
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Total Quizzes</div>
                      <div style={{ fontSize: 20, fontWeight: 700 }}>
                        {inspectedUser.total_quiz_attempts}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Spaces & Projects Overview */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
                {/* Spaces */}
                <div
                  className="card"
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    borderRadius: 8,
                    border: '1px solid var(--border-color)',
                    padding: 16,
                  }}
                >
                  <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 12px 0' }}>
                    📁 Spaces ({inspectedUser.spaces.length})
                  </h3>
                  {inspectedUser.spaces.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {inspectedUser.spaces.map((s) => (
                        <div
                          key={s.id}
                          style={{
                            padding: '8px 12px',
                            borderRadius: 6,
                            backgroundColor: 'var(--bg-main)',
                            display: 'flex',
                            justifyContent: 'space-between',
                          }}
                        >
                          <div>
                            <div style={{ fontWeight: 600, fontSize: 14 }}>{s.name}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{s.description || 'No description'}</div>
                          </div>
                          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                            {s.projects_count} projects
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No study spaces created yet.</p>
                  )}
                </div>

                {/* Projects */}
                <div
                  className="card"
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    borderRadius: 8,
                    border: '1px solid var(--border-color)',
                    padding: 16,
                  }}
                >
                  <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 12px 0' }}>
                    📂 Projects ({inspectedUser.projects.length})
                  </h3>
                  {inspectedUser.projects.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {inspectedUser.projects.map((p) => (
                        <div
                          key={p.id}
                          style={{
                            padding: '8px 12px',
                            borderRadius: 6,
                            backgroundColor: 'var(--bg-main)',
                            display: 'flex',
                            justifyContent: 'space-between',
                          }}
                        >
                          <div>
                            <div style={{ fontWeight: 600, fontSize: 14 }}>{p.name}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                              Space: {p.space_name} · {p.materials_count} files
                            </div>
                          </div>
                          <span style={{ fontWeight: 600, color: 'var(--primary)', fontSize: 13 }}>
                            {p.mastery_score}% mastery
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No projects created yet.</p>
                  )}
                </div>
              </div>

              {/* Concept Mastery & Assessments */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
                {/* Concept Mastery Breakdown */}
                <div
                  className="card"
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    borderRadius: 8,
                    border: '1px solid var(--border-color)',
                    padding: 16,
                  }}
                >
                  <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 12px 0' }}>
                    🎯 Concept Mastery Breakdown
                  </h3>
                  {inspectedUser.mastery_breakdown.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 300, overflowY: 'auto' }}>
                      {inspectedUser.mastery_breakdown.map((m, idx) => (
                        <div
                          key={idx}
                          style={{
                            padding: '8px 12px',
                            borderRadius: 6,
                            backgroundColor: 'var(--bg-main)',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                          }}
                        >
                          <div>
                            <div style={{ fontWeight: 600, fontSize: 13 }}>{m.concept}</div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                              Status: <strong>{m.status}</strong> · Mistakes: {m.recent_mistakes} · Confidence: {m.confidence}
                            </div>
                          </div>
                          <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--primary)' }}>
                            {m.mastery_score}%
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No concept masteries recorded.</p>
                  )}
                </div>

                {/* Completed Assessments */}
                <div
                  className="card"
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    borderRadius: 8,
                    border: '1px solid var(--border-color)',
                    padding: 16,
                  }}
                >
                  <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 12px 0' }}>
                    📝 Completed Assessments ({inspectedUser.completed_assessments.length})
                  </h3>
                  {inspectedUser.completed_assessments.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 300, overflowY: 'auto' }}>
                      {inspectedUser.completed_assessments.map((a) => (
                        <div
                          key={a.id}
                          style={{
                            padding: '8px 12px',
                            borderRadius: 6,
                            backgroundColor: 'var(--bg-main)',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                          }}
                        >
                          <div>
                            <div style={{ fontWeight: 600, fontSize: 13 }}>
                              Assessment #{a.id} (Project {a.project_id})
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                              {a.total_questions} questions · Completed {a.completed_at}
                            </div>
                          </div>
                          <span
                            style={{
                              fontSize: 14,
                              fontWeight: 700,
                              color: a.overall_score >= 70 ? '#10b981' : '#f59e0b',
                            }}
                          >
                            {a.overall_score} / 100
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No assessments completed yet.</p>
                  )}
                </div>
              </div>

              {/* User Activity Feed */}
              <div
                className="card"
                style={{
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: 8,
                  border: '1px solid var(--border-color)',
                  padding: 16,
                }}
              >
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 12px 0' }}>
                  🕒 Recent User Activity (Latest 20 Events)
                </h3>
                {inspectedUser.activities.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 300, overflowY: 'auto' }}>
                    {inspectedUser.activities.map((act) => (
                      <div
                        key={act.id}
                        style={{
                          padding: '8px 12px',
                          borderRadius: 6,
                          backgroundColor: 'var(--bg-main)',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          fontSize: 13,
                        }}
                      >
                        <div>
                          <span style={{ fontWeight: 600, color: 'var(--primary)' }}>{act.event_type}</span>
                          <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>
                            Project: {act.project_id || 'General'}
                          </span>
                        </div>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          {formatTime(act.created_at)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No activity events found for this user.</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: AI USAGE & COSTS */}
      {!isLoading && activeTab === 'ai-usage' && aiUsage && (
        <div>
          {/* Top Metric Cards */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: 16,
              marginBottom: 24,
            }}
          >
            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 16,
              }}
            >
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Total AI Requests</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--primary)', marginTop: 6 }}>
                {aiUsage.total_requests.toLocaleString()}
              </div>
            </div>

            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 16,
              }}
            >
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Success Rate</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#10b981', marginTop: 6 }}>
                {aiUsage.success_rate}%
              </div>
            </div>

            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 16,
              }}
            >
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Average Latency</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#f59e0b', marginTop: 6 }}>
                {aiUsage.latency_stats.avg_latency_ms} ms
              </div>
            </div>

            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 16,
              }}
            >
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Token Usage</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-main)', marginTop: 6 }}>
                {aiUsage.token_usage.display_text}
              </div>
            </div>

            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 16,
              }}
            >
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Estimated Cost</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-muted)', marginTop: 6 }}>
                {aiUsage.estimated_cost.display_text}
              </div>
            </div>
          </div>

          {/* Breakdown Grids */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
            {/* Feature Breakdown */}
            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 18,
              }}
            >
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 14px 0' }}>
                📊 Usage by Feature
              </h3>
              {Object.keys(aiUsage.feature_breakdown).length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {Object.entries(aiUsage.feature_breakdown).map(([feat, count]) => (
                    <div key={feat}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                        <span style={{ fontWeight: 600 }}>{feat}</span>
                        <span style={{ color: 'var(--text-muted)' }}>{count} calls</span>
                      </div>
                      <div
                        style={{
                          height: 8,
                          borderRadius: 4,
                          backgroundColor: 'var(--bg-main)',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            height: '100%',
                            width: `${Math.min(100, Math.round((count / (aiUsage.total_requests || 1)) * 100))}%`,
                            backgroundColor: 'var(--primary)',
                            borderRadius: 4,
                          }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No feature usage recorded yet.</p>
              )}
            </div>

            {/* Model Breakdown */}
            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 18,
              }}
            >
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 14px 0' }}>
                🤖 Models Utilized
              </h3>
              {Object.keys(aiUsage.model_breakdown).length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {Object.entries(aiUsage.model_breakdown).map(([mdl, count]) => (
                    <div
                      key={mdl}
                      style={{
                        padding: '10px 14px',
                        borderRadius: 6,
                        backgroundColor: 'var(--bg-main)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{mdl}</span>
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: 12,
                          backgroundColor: 'var(--primary)',
                          color: '#fff',
                          fontSize: 12,
                          fontWeight: 600,
                        }}
                      >
                        {count} calls
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No models recorded.</p>
              )}
            </div>
          </div>

          {/* Recent AI Requests Table */}
          <div
            className="card"
            style={{
              backgroundColor: 'var(--bg-card)',
              borderRadius: 8,
              border: '1px solid var(--border-color)',
              overflow: 'hidden',
            }}
          >
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
                📋 Recent AI Requests (Latest 100)
              </h3>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--bg-main)', borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ padding: '10px 16px' }}>ID</th>
                  <th style={{ padding: '10px 16px' }}>Feature</th>
                  <th style={{ padding: '10px 16px' }}>Model</th>
                  <th style={{ padding: '10px 16px' }}>Latency</th>
                  <th style={{ padding: '10px 16px' }}>Status</th>
                  <th style={{ padding: '10px 16px' }}>User / Project</th>
                  <th style={{ padding: '10px 16px' }}>Time</th>
                </tr>
              </thead>
              <tbody>
                {aiUsage.recent_requests.map((r) => (
                  <tr key={r.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '10px 16px', color: 'var(--text-muted)' }}>#{r.id}</td>
                    <td style={{ padding: '10px 16px', fontWeight: 600 }}>{r.feature}</td>
                    <td style={{ padding: '10px 16px' }}>{r.model || 'default'}</td>
                    <td style={{ padding: '10px 16px' }}>{r.latency_ms ? `${r.latency_ms} ms` : 'N/A'}</td>
                    <td style={{ padding: '10px 16px' }}>
                      <span
                        style={{
                          fontSize: 11,
                          padding: '2px 6px',
                          borderRadius: 4,
                          backgroundColor: r.success ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                          color: r.success ? '#10b981' : '#ef4444',
                          fontWeight: 600,
                        }}
                      >
                        {r.success ? 'SUCCESS' : 'FAILED'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 16px', color: 'var(--text-muted)' }}>
                      User {r.user_id || 'N/A'} / Proj {r.project_id || 'N/A'}
                    </td>
                    <td style={{ padding: '10px 16px', color: 'var(--text-muted)', fontSize: 12 }}>
                      {formatTime(r.created_at)}
                    </td>
                  </tr>
                ))}
                {aiUsage.recent_requests.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
                      No AI requests logged yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: AI EVALUATION & BENCHMARKS */}
      {!isLoading && activeTab === 'evaluation' && aiEvaluation && (
        <div>
          {/* Evaluation Metrics Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
            {/* Tutor Evaluation */}
            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 18,
              }}
            >
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 14px 0', color: 'var(--text-main)' }}>
                📖 AI Tutor Grounding & Retrieval
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div style={{ padding: 12, borderRadius: 6, backgroundColor: 'var(--bg-main)' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Grounded Answer Rate</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: '#10b981', marginTop: 4 }}>
                    {aiEvaluation.tutor_evaluation.grounded_rate}%
                  </div>
                </div>
                <div style={{ padding: 12, borderRadius: 6, backgroundColor: 'var(--bg-main)' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Total Sources Cited</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--primary)', marginTop: 4 }}>
                    {aiEvaluation.tutor_evaluation.sources_cited_count}
                  </div>
                </div>
                <div style={{ padding: 12, borderRadius: 6, backgroundColor: 'var(--bg-main)' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Total Questions Evaluated</div>
                  <div style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>
                    {aiEvaluation.tutor_evaluation.total_questions}
                  </div>
                </div>
                <div style={{ padding: 12, borderRadius: 6, backgroundColor: 'var(--bg-main)' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Grounded Queries</div>
                  <div style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>
                    {aiEvaluation.tutor_evaluation.grounded_questions_count}
                  </div>
                </div>
              </div>
            </div>

            {/* Assessment Evaluation */}
            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 18,
              }}
            >
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 14px 0', color: 'var(--text-main)' }}>
                🎯 Assessment & Grading Rubric
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div style={{ padding: 12, borderRadius: 6, backgroundColor: 'var(--bg-main)' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Average Student Score</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--primary)', marginTop: 4 }}>
                    {aiEvaluation.assessment_evaluation.average_score} / 100
                  </div>
                </div>
                <div style={{ padding: 12, borderRadius: 6, backgroundColor: 'var(--bg-main)' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Total Evaluations</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: '#6366f1', marginTop: 4 }}>
                    {aiEvaluation.assessment_evaluation.total_evaluations}
                  </div>
                </div>
                <div style={{ padding: 12, borderRadius: 6, backgroundColor: 'var(--bg-main)' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Strengths Identified</div>
                  <div style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>
                    {aiEvaluation.assessment_evaluation.strengths_identified_count}
                  </div>
                </div>
                <div style={{ padding: 12, borderRadius: 6, backgroundColor: 'var(--bg-main)' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Missing Concepts Tagged</div>
                  <div style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>
                    {aiEvaluation.assessment_evaluation.missing_concepts_identified_count}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Evaluation Test Suite Runner */}
          <div
            className="card"
            style={{
              backgroundColor: 'var(--bg-card)',
              borderRadius: 8,
              border: '1px solid var(--border-color)',
              padding: 20,
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 16,
              }}
            >
              <div>
                <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
                  🧪 Basic Evaluation Test Benchmark Suite
                </h3>
                <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '4px 0 0 0' }}>
                  Verifies grounded synthesis, code generation accuracy, and unsupported query safety rejection.
                </p>
              </div>
              <button
                onClick={handleRunEvaluation}
                className="btn btn-primary btn-sm"
                disabled={isRunningEvaluation}
              >
                {isRunningEvaluation ? '⏳ Running Suite...' : '🚀 Re-run Benchmark Suite'}
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {aiEvaluation.benchmark_results.map((bm, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '12px 16px',
                    borderRadius: 6,
                    backgroundColor: 'var(--bg-main)',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div style={{ maxWidth: '75%' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ fontWeight: 700, fontSize: 14 }}>{bm.test_name}</span>
                      <span
                        style={{
                          fontSize: 11,
                          padding: '1px 6px',
                          borderRadius: 4,
                          backgroundColor: 'rgba(99, 102, 241, 0.15)',
                          color: '#6366f1',
                          fontWeight: 600,
                        }}
                      >
                        {bm.category}
                      </span>
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-main)', marginTop: 4 }}>
                      Query: <em>"{bm.input_query}"</em>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                      {bm.details}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span
                      style={{
                        padding: '4px 10px',
                        borderRadius: 4,
                        fontWeight: 700,
                        fontSize: 12,
                        backgroundColor: bm.status === 'PASS' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                        color: bm.status === 'PASS' ? '#10b981' : '#ef4444',
                      }}
                    >
                      {bm.status}
                    </span>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                      {bm.latency_ms} ms
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: SYSTEM HEALTH */}
      {!isLoading && activeTab === 'health' && systemHealth && (
        <div>
          {/* Health Status Cards */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: 16,
              marginBottom: 24,
            }}
          >
            {/* API Status */}
            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 16,
              }}
            >
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>API Status</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
                <span
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    backgroundColor: systemHealth.api_status === 'healthy' ? '#10b981' : '#ef4444',
                  }}
                ></span>
                <span style={{ fontSize: 20, fontWeight: 700, textTransform: 'capitalize' }}>
                  {systemHealth.api_status}
                </span>
              </div>
            </div>

            {/* Database */}
            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 16,
              }}
            >
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Database Connectivity</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#10b981', marginTop: 6 }}>
                {systemHealth.database.status?.toUpperCase()}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                Engine: {systemHealth.database.engine} · Latency: {systemHealth.database.latency_ms} ms
              </div>
            </div>

            {/* AI Provider */}
            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 16,
              }}
            >
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>AI Provider Status</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#3b82f6', marginTop: 6 }}>
                {systemHealth.ai_provider.status?.toUpperCase()}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                Mode: {systemHealth.ai_provider.mode}
              </div>
            </div>

            {/* Background Processing Queue */}
            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 16,
              }}
            >
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Background Processing</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#f59e0b', marginTop: 6 }}>
                {systemHealth.background_queue.status?.toUpperCase()}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                Backlog: {systemHealth.background_queue.backlog} items ({systemHealth.background_queue.queued_count} queued)
              </div>
            </div>
          </div>

          {/* AI Metrics Row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 18,
              }}
            >
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 10px 0' }}>
                ⚡ Average AI Latency
              </h3>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--primary)' }}>
                {systemHealth.average_ai_latency_ms} ms
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '6px 0 0 0' }}>
                Computed across all grounded tutor, quiz generation, and rubric grading calls.
              </p>
            </div>

            <div
              className="card"
              style={{
                backgroundColor: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                padding: 18,
              }}
            >
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 10px 0' }}>
                ⚠️ AI Error Rate
              </h3>
              <div
                style={{
                  fontSize: 28,
                  fontWeight: 700,
                  color: systemHealth.ai_error_rate > 5 ? '#ef4444' : '#10b981',
                }}
              >
                {systemHealth.ai_error_rate}%
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '6px 0 0 0' }}>
                Total recorded AI failures: {systemHealth.ai_error_count}
              </p>
            </div>
          </div>

          {/* Recent Failures Log */}
          <div
            className="card"
            style={{
              backgroundColor: 'var(--bg-card)',
              borderRadius: 8,
              border: '1px solid var(--border-color)',
              padding: 18,
            }}
          >
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 14px 0' }}>
              🚨 Recent Failures & Alerts (Zero Secrets Exposed)
            </h3>
            {systemHealth.recent_failures && systemHealth.recent_failures.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {systemHealth.recent_failures.map((f, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '10px 14px',
                      borderRadius: 6,
                      backgroundColor: 'var(--bg-main)',
                      border: '1px solid rgba(239, 68, 68, 0.2)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <span
                        style={{
                          fontSize: 11,
                          padding: '2px 6px',
                          borderRadius: 4,
                          backgroundColor: '#ef4444',
                          color: '#fff',
                          fontWeight: 700,
                          marginRight: 8,
                        }}
                      >
                        {f.type}
                      </span>
                      <strong style={{ fontSize: 13 }}>{f.target}</strong>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                        {f.detail}
                      </div>
                    </div>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{f.timestamp}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div
                style={{
                  padding: 24,
                  textAlign: 'center',
                  backgroundColor: 'var(--bg-main)',
                  borderRadius: 6,
                  color: '#10b981',
                  fontWeight: 600,
                  fontSize: 14,
                }}
              >
                ✅ All systems running smoothly. No recent failures or unhandled exceptions recorded.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
