import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Modal } from '../components/Modal';
import { EmptyState } from '../components/EmptyState';

export function DashboardPage() {
  const { user } = useAuth();
  const [spaces, setSpaces] = useState([]);
  const [activities, setActivities] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newSpaceName, setNewSpaceName] = useState('');
  const [newSpaceDesc, setNewSpaceDesc] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const loadDashboardData = async () => {
    setIsLoading(true);
    try {
      const [spacesData, activitiesData] = await Promise.all([
        api.spaces.list(),
        api.activity.list(10),
      ]);
      setSpaces(spacesData);
      setActivities(activitiesData);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const totalProjects = spaces.reduce((acc, s) => acc + (s.project_count || 0), 0);

  const handleCreateSpace = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await api.spaces.create({
        name: newSpaceName,
        description: newSpaceDesc,
      });
      setNewSpaceName('');
      setNewSpaceDesc('');
      setIsModalOpen(false);
      await loadDashboardData();
    } catch (err) {
      setError(err.message || 'Failed to create space');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatActivityText = (event) => {
    const meta = event.metadata || {};
    switch (event.event_type) {
      case 'SPACE_CREATED':
        return `Created space "${meta.space_name || 'New Space'}"`;
      case 'PROJECT_CREATED':
        return `Created project "${meta.project_name || 'New Project'}" in "${meta.space_name || 'Space'}"`;
      case 'MATERIAL_UPLOADED':
        return `Uploaded material "${meta.filename || 'PDF'}" to project`;
      case 'MATERIAL_PROCESSING_STARTED':
        return `Processing started for "${meta.filename || 'PDF'}"`;
      case 'MATERIAL_PROCESSED':
        return `Ready: processed "${meta.filename || 'PDF'}" successfully`;
      case 'MATERIAL_PROCESSING_FAILED':
        return `Failed processing "${meta.filename || 'PDF'}"`;
      default:
        return event.event_type.replace(/_/g, ' ');
    }
  };

  const formatTime = (dateStr) => {
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
    <div className="content-body">
      <div className="page-header">
        <div>
          <h1 className="page-title">Welcome back, {user?.name || 'Student'}! 👋</h1>
          <p className="page-subtitle">Here is an overview of your study environment and recent progress.</p>
        </div>
        <button onClick={() => setIsModalOpen(true)} className="btn btn-primary">
          <span>+</span> Create Space
        </button>
      </div>

      {/* Stats Summary */}
      <div className="stat-grid">
        <div className="stat-card">
          <div>
            <div className="stat-val">{spaces.length}</div>
            <div className="stat-label">Study Spaces</div>
          </div>
          <div style={{ fontSize: 32 }}>📁</div>
        </div>

        <div className="stat-card">
          <div>
            <div className="stat-val">{totalProjects}</div>
            <div className="stat-label">Active Projects</div>
          </div>
          <div style={{ fontSize: 32 }}>📖</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24 }}>
        {/* Quick Spaces List */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700 }}>Your Study Spaces</h2>
            <Link to="/spaces" style={{ fontSize: 14, fontWeight: 600 }}>
              View all &rarr;
            </Link>
          </div>

          {isLoading ? (
            <div className="card" style={{ textAlign: 'center', padding: 40 }}>
              <span className="spinner"></span>
            </div>
          ) : spaces.length === 0 ? (
            <EmptyState
              icon="📁"
              title="No Study Spaces yet"
              description="Spaces help you organize projects by subject, semester, or topic."
              action={
                <button onClick={() => setIsModalOpen(true)} className="btn btn-primary">
                  Create your first Space
                </button>
              }
            />
          ) : (
            <div className="grid-cards" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
              {spaces.slice(0, 4).map((space) => (
                <div key={space.id} className="card">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                    <span style={{ fontSize: 20 }}>📁</span>
                    <h3 style={{ fontSize: 16, fontWeight: 600 }}>{space.name}</h3>
                  </div>
                  <p style={{ fontSize: 13, color: 'var(--text-muted)', minHeight: 38, marginBottom: 14 }}>
                    {space.description || 'No description provided.'}
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border)', paddingTop: 12 }}>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      {space.project_count || 0} {space.project_count === 1 ? 'project' : 'projects'}
                    </span>
                    <Link to={`/spaces/${space.id}`} className="btn btn-secondary btn-sm">
                      Open Space &rarr;
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Activity Feed */}
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>Recent Activity</h2>
          <div className="card">
            {isLoading ? (
              <div style={{ textAlign: 'center', padding: 20 }}>
                <span className="spinner"></span>
              </div>
            ) : activities.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px 12px', color: 'var(--text-muted)', fontSize: 14 }}>
                No recent activity recorded yet.
              </div>
            ) : (
              <div className="activity-feed">
                {activities.map((event) => (
                  <div key={event.id} className="activity-item">
                    <div className="activity-dot" />
                    <div className="activity-body">
                      <div className="activity-text">{formatActivityText(event)}</div>
                      <div className="activity-time">{formatTime(event.created_at)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Space Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create New Study Space"
        footer={
          <>
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="btn btn-secondary"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="create-space-form"
              className="btn btn-primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? <span className="spinner"></span> : 'Create Space'}
            </button>
          </>
        }
      >
        {error && <div className="alert alert-danger">{error}</div>}
        <form id="create-space-form" onSubmit={handleCreateSpace}>
          <div className="form-group">
            <label className="form-label">Space Name</label>
            <input
              type="text"
              className="form-input"
              value={newSpaceName}
              onChange={(e) => setNewSpaceName(e.target.value)}
              placeholder="e.g. Computer Science, Physics 101"
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Description (Optional)</label>
            <textarea
              className="form-textarea"
              value={newSpaceDesc}
              onChange={(e) => setNewSpaceDesc(e.target.value)}
              placeholder="What subjects or goals are covered here?"
            />
          </div>
        </form>
      </Modal>
    </div>
  );
}
