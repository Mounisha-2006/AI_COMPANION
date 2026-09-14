import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { EmptyState } from '../components/EmptyState';

export function GlobalAnalyticsPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const loadAnalytics = async () => {
    setIsLoading(true);
    setError('');
    try {
      const res = await api.analytics.getGlobal();
      setData(res);
    } catch (err) {
      console.error('Failed to load global analytics:', err);
      setError(err.message || 'Failed to load analytics data.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

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

  const formatActivityText = (event) => {
    const meta = event.metadata || {};
    switch (event.event_type) {
      case 'SPACE_CREATED':
        return `Created space "${meta.space_name || 'New Space'}"`;
      case 'PROJECT_CREATED':
        return `Created project "${meta.project_name || 'New Project'}"`;
      case 'PROJECT_ACCESSED':
        return `Accessed project "${meta.project_name || 'Project'}"`;
      case 'MATERIAL_UPLOADED':
        return `Uploaded material "${meta.filename || 'PDF'}"`;
      case 'MATERIAL_PROCESSED':
        return `Processed "${meta.filename || 'PDF'}" (${meta.chunk_count || 0} chunks)`;
      case 'MATERIAL_PROCESSING_FAILED':
        return `Failed processing "${meta.filename || 'PDF'}"`;
      case 'TUTOR_QUESTION':
        return `Asked AI Tutor: "${meta.question_preview || 'Study question'}"`;
      case 'TUTOR_CONVERSATION_STARTED':
        return `Started a new AI Tutor study session`;
      case 'QUIZ_STARTED':
        return `Started adaptive quiz (${meta.total_questions || 5} questions)`;
      case 'QUESTION_ANSWERED':
        return `Answered question on "${meta.concept || 'Concept'}" (${meta.is_correct ? 'Correct' : 'Incorrect'})`;
      case 'QUIZ_COMPLETED':
        return `Completed quiz with score ${meta.score || 0}/${meta.total_questions || 5} (${meta.percentage || 0}%)`;
      case 'ASSESSMENT_STARTED':
        return `Started knowledge assessment`;
      case 'ASSESSMENT_COMPLETED':
        return `Completed assessment with score ${meta.overall_score || 0}/100`;
      case 'MASTERY_UPDATED':
        return `Updated mastery on "${meta.concept || 'Concept'}" to ${meta.mastery_score || 0}%`;
      case 'GROWTH_VIEWED':
        return `Viewed growth analysis report`;
      case 'RECOMMENDATION_GENERATED':
        return `Received AI study recommendations`;
      default:
        return event.event_type.replace(/_/g, ' ');
    }
  };

  if (isLoading) {
    return (
      <div className="content-body" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
          <div style={{ fontSize: '32px', marginBottom: '12px' }}>📊</div>
          <div>Loading your learning analytics...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="content-body">
        <div className="card" style={{ padding: '24px', textAlign: 'center', borderColor: 'var(--danger)' }}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>⚠️</div>
          <div style={{ color: 'var(--danger)', fontWeight: 600, marginBottom: '12px' }}>{error}</div>
          <button onClick={loadAnalytics} className="btn btn-primary btn-sm">Retry</button>
        </div>
      </div>
    );
  }

  const maxTimelineCount = Math.max(...(data.learning_activity_over_time?.map(p => p.count) || [1]), 1);

  return (
    <div className="content-body">
      {/* Page Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Learning Analytics & Progress 📈</h1>
          <p className="page-subtitle">
            Cross-project performance, mastery trends, and learning activity for {user?.name || 'Student'}.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span className="badge" style={{ background: 'var(--primary-light)', color: 'var(--primary)', padding: '6px 12px', fontSize: '13px', borderRadius: '16px', fontWeight: 600 }}>
            🗓️ {data.active_days} Active {data.active_days === 1 ? 'Day' : 'Days'}
          </span>
          <button onClick={loadAnalytics} className="btn btn-secondary btn-sm" title="Refresh data">
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Overview Stat Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        {/* 1. Overall Mastery */}
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>OVERALL MASTERY</span>
            <span style={{ fontSize: '20px' }}>🎯</span>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 800, color: data.overall_mastery >= 75 ? 'var(--success)' : data.overall_mastery >= 50 ? 'var(--primary)' : 'var(--warning)' }}>
            {data.overall_mastery}%
          </div>
          <div style={{ width: '100%', background: 'var(--border)', height: '6px', borderRadius: '3px', marginTop: '10px', overflow: 'hidden' }}>
            <div style={{ width: `${Math.min(data.overall_mastery, 100)}%`, height: '100%', background: data.overall_mastery >= 75 ? 'var(--success)' : 'var(--primary)', borderRadius: '3px', transition: 'width 0.5s ease' }} />
          </div>
        </div>

        {/* 2. Total Activity */}
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>TOTAL ACTIVITY</span>
            <span style={{ fontSize: '20px' }}>⚡</span>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-main)' }}>
            {data.total_learning_activity}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
            Events across {data.total_projects} {data.total_projects === 1 ? 'project' : 'projects'}
          </div>
        </div>

        {/* 3. Quiz Accuracy */}
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>QUIZ ACCURACY</span>
            <span style={{ fontSize: '20px' }}>🏆</span>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-main)' }}>
            {data.quiz_activity.quiz_accuracy}%
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
            {data.quiz_activity.quizzes_completed} completed / {data.quiz_activity.quizzes_started} started
          </div>
        </div>

        {/* 4. Assessment Performance */}
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>ASSESSMENT AVG</span>
            <span style={{ fontSize: '20px' }}>📝</span>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 800, color: data.average_assessment_performance !== null ? 'var(--text-main)' : 'var(--text-muted)' }}>
            {data.average_assessment_performance !== null ? `${data.average_assessment_performance}%` : 'N/A'}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
            {data.assessment_performance.assessments_completed} completed assessments
          </div>
        </div>

        {/* 5. Tutor & Questions */}
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>QUESTIONS ASKED</span>
            <span style={{ fontSize: '20px' }}>🤖</span>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-main)' }}>
            {data.questions_asked}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
            {data.tutor_interactions} Tutor questions | {data.ai_generated_feedback} AI feedback
          </div>
        </div>
      </div>

      {/* Learning Activity Timeline (Last 14 Days) */}
      <div className="card" style={{ padding: '24px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)' }}>Learning Activity (Last 14 Days)</h2>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Daily learning events recorded across all your projects</div>
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Total: {data.learning_activity_over_time?.reduce((acc, p) => acc + p.count, 0) || 0} events
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'flex-end', height: '140px', gap: '8px', paddingTop: '16px' }}>
          {data.learning_activity_over_time?.map((pt, idx) => {
            const heightPercent = pt.count > 0 ? Math.max((pt.count / maxTimelineCount) * 100, 15) : 4;
            const isToday = idx === (data.learning_activity_over_time.length - 1);
            return (
              <div
                key={pt.date}
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  height: '100%',
                  justifyContent: 'flex-end',
                }}
                title={`${pt.date}: ${pt.count} events`}
              >
                <span style={{ fontSize: '11px', color: pt.count > 0 ? 'var(--text-main)' : 'transparent', fontWeight: 600, marginBottom: '4px' }}>
                  {pt.count > 0 ? pt.count : ''}
                </span>
                <div
                  style={{
                    width: '100%',
                    height: `${heightPercent}%`,
                    background: isToday ? 'var(--primary)' : pt.count > 0 ? '#818cf8' : 'var(--border)',
                    borderRadius: '4px 4px 0 0',
                    transition: 'all 0.3s ease',
                  }}
                />
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '6px', whiteSpace: 'nowrap' }}>
                  {pt.date.slice(5)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Two Column Section: Concepts Health & Projects Performance */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px', marginBottom: '24px' }}>
        {/* Concept Health */}
        <div className="card" style={{ padding: '24px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px' }}>Concept Health Summary</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'var(--success-light)', borderRadius: 'var(--radius-md)' }}>
              <div>
                <div style={{ fontWeight: 600, color: '#065f46' }}>Concepts Improving</div>
                <div style={{ fontSize: '12px', color: '#047857' }}>Growing mastery and successful retention</div>
              </div>
              <span style={{ fontSize: '22px', fontWeight: 800, color: '#065f46' }}>
                {data.concepts_improving}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'var(--warning-light)', borderRadius: 'var(--radius-md)' }}>
              <div>
                <div style={{ fontWeight: 600, color: '#92400e' }}>Requires Attention</div>
                <div style={{ fontSize: '12px', color: '#b45309' }}>Low mastery or recent quiz/assessment mistakes</div>
              </div>
              <span style={{ fontSize: '22px', fontWeight: 800, color: '#92400e' }}>
                {data.concepts_requiring_attention}
              </span>
            </div>
          </div>
        </div>

        {/* Assessment Performance History */}
        <div className="card" style={{ padding: '24px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px' }}>Recent Assessments</h2>
          {data.assessment_performance.history?.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {data.assessment_performance.history.map((a) => (
                <div key={a.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)' }}>
                  <div>
                    <span style={{ fontWeight: 600 }}>Assessment #{a.id}</span>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '8px' }}>{a.date}</span>
                  </div>
                  <span className="badge" style={{ fontWeight: 700, background: a.score >= 70 ? 'var(--success-light)' : 'var(--warning-light)', color: a.score >= 70 ? 'var(--success)' : 'var(--warning)' }}>
                    {a.score}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '24px 0' }}>
              No assessments completed yet. Take an assessment inside a project to see your score trends here.
            </div>
          )}
        </div>
      </div>

      {/* Projects Breakdown Table */}
      <div className="card" style={{ padding: '24px', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px' }}>Projects Breakdown</h2>
        {data.projects_breakdown?.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '10px 12px' }}>Project</th>
                  <th style={{ padding: '10px 12px' }}>Space</th>
                  <th style={{ padding: '10px 12px' }}>Mastery</th>
                  <th style={{ padding: '10px 12px' }}>Quizzes</th>
                  <th style={{ padding: '10px 12px' }}>Tutor Qs</th>
                  <th style={{ padding: '10px 12px' }}>Materials</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {data.projects_breakdown.map((p) => (
                  <tr key={p.project_id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '12px', fontWeight: 600 }}>
                      <Link to={`/projects/${p.project_id}`} style={{ color: 'var(--text-main)' }}>
                        {p.project_name}
                      </Link>
                    </td>
                    <td style={{ padding: '12px', color: 'var(--text-muted)' }}>{p.space_name}</td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '60px', background: 'var(--border)', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ width: `${Math.min(p.mastery_score, 100)}%`, height: '100%', background: p.mastery_score >= 70 ? 'var(--success)' : 'var(--primary)', borderRadius: '3px' }} />
                        </div>
                        <span style={{ fontWeight: 600 }}>{p.mastery_score}%</span>
                      </div>
                    </td>
                    <td style={{ padding: '12px' }}>{p.quiz_count}</td>
                    <td style={{ padding: '12px' }}>{p.tutor_questions}</td>
                    <td style={{ padding: '12px' }}>{p.materials_count}</td>
                    <td style={{ padding: '12px', textAlign: 'right' }}>
                      <Link to={`/projects/${p.project_id}`} className="btn btn-secondary btn-sm" style={{ padding: '4px 8px', fontSize: '12px' }}>
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon="📁"
            title="No projects yet"
            description="Create study spaces and projects to track your progress and performance."
          />
        )}
      </div>

      {/* Recent Activity Feed */}
      <div className="card" style={{ padding: '24px' }}>
        <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px' }}>Recent Activity Feed</h2>
        {data.recent_activities?.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {data.recent_activities.map((ev) => (
              <div key={ev.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)' }}>
                <div>
                  <div style={{ fontWeight: 500, color: 'var(--text-main)' }}>{formatActivityText(ev)}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{ev.event_type}</div>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', whiteSpace: 'nowrap', marginLeft: '12px' }}>
                  {formatTime(ev.created_at)}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '24px 0' }}>
            No activity events recorded yet.
          </div>
        )}
      </div>
    </div>
  );
}
