import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Modal } from '../components/Modal';
import { EmptyState } from '../components/EmptyState';

export function SpaceDetailPage() {
  const { spaceId } = useParams();
  const navigate = useNavigate();

  const [space, setSpace] = useState(null);
  const [projects, setProjects] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [projName, setProjName] = useState('');
  const [projDesc, setProjDesc] = useState('');
  const [projGoal, setProjGoal] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [spaceData, projectsData] = await Promise.all([
        api.spaces.get(spaceId),
        api.projects.list(spaceId),
      ]);
      setSpace(spaceData);
      setProjects(projectsData);
    } catch (err) {
      console.error('Failed to load space details:', err);
      if (err.status === 404) {
        navigate('/spaces');
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [spaceId]);

  const handleCreateProject = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await api.projects.create(spaceId, {
        name: projName,
        description: projDesc,
        learning_goal: projGoal,
      });
      setProjName('');
      setProjDesc('');
      setProjGoal('');
      setIsModalOpen(false);
      await loadData();
    } catch (err) {
      setError(err.message || 'Failed to create project.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteProject = async (projectId, projectName, e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(`Delete project "${projectName}" and its materials?`)) {
      return;
    }
    try {
      await api.projects.delete(projectId);
      await loadData();
    } catch (err) {
      alert(err.message || 'Failed to delete project');
    }
  };

  if (isLoading) {
    return (
      <div className="content-body" style={{ textAlign: 'center', padding: 80 }}>
        <span className="spinner"></span>
      </div>
    );
  }

  if (!space) {
    return (
      <div className="content-body">
        <EmptyState
          title="Space Not Found"
          description="This space does not exist or you don't have access to it."
          action={<Link to="/spaces" className="btn btn-primary">Back to Spaces</Link>}
        />
      </div>
    );
  }

  return (
    <div className="content-body">
      <div className="breadcrumbs">
        <Link to="/spaces">Spaces</Link>
        <span>/</span>
        <span>{space.name}</span>
      </div>

      <div className="page-header">
        <div>
          <h1 className="page-title">{space.name}</h1>
          <p className="page-subtitle">{space.description || 'No description for this study space.'}</p>
        </div>
        <button onClick={() => setIsModalOpen(true)} className="btn btn-primary">
          <span>+</span> Create Project
        </button>
      </div>

      {projects.length === 0 ? (
        <EmptyState
          icon="📖"
          title="No Projects in this Space"
          description="Projects represent specific topics, modules, or assignments where you study materials."
          action={
            <button onClick={() => setIsModalOpen(true)} className="btn btn-primary">
              Create First Project
            </button>
          }
        />
      ) : (
        <div className="grid-cards">
          {projects.map((proj) => (
            <div key={proj.id} className="card" style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-main)' }}>{proj.name}</h3>
                <button
                  onClick={(e) => handleDeleteProject(proj.id, proj.name, e)}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-muted)',
                    fontSize: 14,
                  }}
                  title="Delete project"
                >
                  🗑️
                </button>
              </div>

              {proj.learning_goal && (
                <div style={{
                  background: 'var(--primary-light)',
                  color: 'var(--primary)',
                  fontSize: 12,
                  fontWeight: 600,
                  padding: '4px 10px',
                  borderRadius: 'var(--radius-sm)',
                  marginTop: 8,
                  display: 'inline-block',
                  alignSelf: 'flex-start'
                }}>
                  🎯 Goal: {proj.learning_goal}
                </div>
              )}

              <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '12px 0', flex: 1 }}>
                {proj.description || 'No description provided.'}
              </p>

              <div style={{ borderTop: '1px solid var(--border)', paddingTop: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  📄 {proj.material_count || 0} {proj.material_count === 1 ? 'material' : 'materials'}
                </span>
                <Link to={`/projects/${proj.id}`} className="btn btn-secondary btn-sm">
                  Open Project &rarr;
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
        title="Create New Project"
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
              form="project-form"
              className="btn btn-primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? <span className="spinner"></span> : 'Create Project'}
            </button>
          </>
        }
      >
        {error && <div className="alert alert-danger">{error}</div>}
        <form id="project-form" onSubmit={handleCreateProject}>
          <div className="form-group">
            <label className="form-label">Project Name</label>
            <input
              type="text"
              className="form-input"
              value={projName}
              onChange={(e) => setProjName(e.target.value)}
              placeholder="e.g. Memory Management & Paging"
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Learning Goal</label>
            <input
              type="text"
              className="form-input"
              value={projGoal}
              onChange={(e) => setProjGoal(e.target.value)}
              placeholder="e.g. Understand page tables, TLB, and virtual address translation"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Description (Optional)</label>
            <textarea
              className="form-textarea"
              value={projDesc}
              onChange={(e) => setProjDesc(e.target.value)}
              placeholder="Key notes, textbook chapters, or focus areas..."
            />
          </div>
        </form>
      </Modal>
    </div>
  );
}
