import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { Modal } from '../components/Modal';
import { EmptyState } from '../components/EmptyState';

export function SpacesPage() {
  const [spaces, setSpaces] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const loadSpaces = async () => {
    setIsLoading(true);
    try {
      const data = await api.spaces.list();
      setSpaces(data);
    } catch (err) {
      console.error('Failed to load spaces:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSpaces();
  }, []);

  const handleCreateSpace = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await api.spaces.create({ name, description });
      setName('');
      setDescription('');
      setIsModalOpen(false);
      await loadSpaces();
    } catch (err) {
      setError(err.message || 'Failed to create space.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteSpace = async (spaceId, spaceName) => {
    if (!window.confirm(`Are you sure you want to delete "${spaceName}"? All its projects and materials will be removed.`)) {
      return;
    }
    try {
      await api.spaces.delete(spaceId);
      await loadSpaces();
    } catch (err) {
      alert(err.message || 'Failed to delete space');
    }
  };

  return (
    <div className="content-body">
      <div className="page-header">
        <div>
          <h1 className="page-title">Study Spaces</h1>
          <p className="page-subtitle">Organize your study domains, modules, and academic subjects.</p>
        </div>
        <button onClick={() => setIsModalOpen(true)} className="btn btn-primary">
          <span>+</span> New Space
        </button>
      </div>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <span className="spinner"></span>
        </div>
      ) : spaces.length === 0 ? (
        <EmptyState
          icon="📁"
          title="No Study Spaces Found"
          description="Create your first study space to begin organizing your projects and materials."
          action={
            <button onClick={() => setIsModalOpen(true)} className="btn btn-primary">
              Create Study Space
            </button>
          }
        />
      ) : (
        <div className="grid-cards">
          {spaces.map((space) => (
            <div key={space.id} className="card" style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 24 }}>📁</span>
                  <div>
                    <h3 style={{ fontSize: 17, fontWeight: 700 }}>{space.name}</h3>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      {space.project_count || 0} {space.project_count === 1 ? 'project' : 'projects'}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteSpace(space.id, space.name)}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-muted)',
                    fontSize: 14,
                    padding: 4,
                  }}
                  title="Delete space"
                >
                  🗑️
                </button>
              </div>

              <p style={{ fontSize: 14, color: 'var(--text-muted)', margin: '14px 0', flex: 1 }}>
                {space.description || 'No description provided.'}
              </p>

              <div style={{ borderTop: '1px solid var(--border)', paddingTop: 14, display: 'flex', justifyContent: 'flex-end' }}>
                <Link to={`/spaces/${space.id}`} className="btn btn-primary btn-sm">
                  View Space &rarr;
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create Study Space"
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
              form="spaces-form"
              className="btn btn-primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? <span className="spinner"></span> : 'Create Space'}
            </button>
          </>
        }
      >
        {error && <div className="alert alert-danger">{error}</div>}
        <form id="spaces-form" onSubmit={handleCreateSpace}>
          <div className="form-group">
            <label className="form-label">Space Name</label>
            <input
              type="text"
              className="form-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Distributed Systems"
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Description (Optional)</label>
            <textarea
              className="form-textarea"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Overview of this study space..."
            />
          </div>
        </form>
      </Modal>
    </div>
  );
}
