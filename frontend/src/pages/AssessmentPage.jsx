import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { EmptyState } from '../components/EmptyState';

export function AssessmentPage() {
  const { projectId } = useParams();

  const [project, setProject] = useState(null);
  const [materials, setMaterials] = useState([]);
  const [masteryData, setMasteryData] = useState({ concepts: [], areas_needing_attention: [] });
  const [assessments, setAssessments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // Active assessment state
  const [activeAssessment, setActiveAssessment] = useState(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [responseText, setResponseText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [evaluation, setEvaluation] = useState(null);
  const [isStarting, setIsStarting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [questionCount, setQuestionCount] = useState(3);

  const loadData = async () => {
    try {
      const [projData, matsData, mastData, assessList] = await Promise.all([
        api.projects.get(projectId),
        api.materials.list(projectId),
        api.mastery.get(projectId),
        api.assessment.list(projectId),
      ]);
      setProject(projData);
      setMaterials(matsData);
      setMasteryData(mastData);
      setAssessments(assessList);
    } catch (err) {
      console.error('Failed to load assessment data:', err);
      setErrorMsg(err.message || 'Failed to load page.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [projectId]);

  const handleStartAssessment = async () => {
    setErrorMsg('');
    setIsStarting(true);
    setEvaluation(null);
    setResponseText('');

    try {
      const newAssessment = await api.assessment.start(projectId, questionCount);
      setActiveAssessment(newAssessment);
      setCurrentQuestionIndex(0);
      await loadData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to start assessment.');
    } finally {
      setIsStarting(false);
    }
  };

  const handleSubmitResponse = async (e) => {
    e.preventDefault();
    if (!responseText.trim() || isSubmitting || !activeAssessment) return;

    setIsSubmitting(true);
    setErrorMsg('');

    const currentQ = activeAssessment.questions[currentQuestionIndex];

    try {
      const evalResult = await api.assessment.submit(
        projectId,
        activeAssessment.id,
        currentQ.id,
        responseText
      );
      setEvaluation(evalResult);

      // Refresh mastery data & assessment details
      const [updatedMastery, updatedAssessment] = await Promise.all([
        api.mastery.get(projectId),
        api.assessment.get(projectId, activeAssessment.id),
      ]);
      setMasteryData(updatedMastery);
      setActiveAssessment(updatedAssessment);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to submit response.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNextQuestion = () => {
    if (!activeAssessment) return;

    if (currentQuestionIndex + 1 < activeAssessment.questions.length) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      setEvaluation(null);
      setResponseText('');
    } else {
      // Completed all questions in this assessment
      setActiveAssessment(null);
      setEvaluation(null);
      setResponseText('');
      loadData();
    }
  };

  const handleReviewAssessment = async (assessId) => {
    try {
      const detail = await api.assessment.get(projectId, assessId);
      setActiveAssessment(detail);
      setCurrentQuestionIndex(0);
      setEvaluation(null);
      setResponseText('');
    } catch (err) {
      alert(err.message || 'Failed to load assessment.');
    }
  };

  const readyMaterialsCount = materials.filter((m) => m.status === 'ready').length;

  const formatDate = (dateStr) => {
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

  if (isLoading) {
    return (
      <div className="content-body" style={{ textAlign: 'center', padding: 80 }}>
        <span className="spinner"></span>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="content-body">
        <EmptyState
          title="Project Not Found"
          description="This project does not exist or you do not have permission to view it."
          action={<Link to="/spaces" className="btn btn-primary">Back to Spaces</Link>}
        />
      </div>
    );
  }

  const currentQ = activeAssessment?.questions ? activeAssessment.questions[currentQuestionIndex] : null;
  const existingResponseForQ = activeAssessment?.responses?.find((r) => r.question_id === currentQ?.id);

  return (
    <div className="content-body">
      {/* Breadcrumbs */}
      <div className="breadcrumbs">
        <Link to="/spaces">Spaces</Link>
        <span>/</span>
        <Link to={`/spaces/${project.space_id}`}>Space</Link>
        <span>/</span>
        <Link to={`/projects/${project.id}`}>{project.name}</Link>
        <span>/</span>
        <span>Open-Ended Assessment & Mastery</span>
      </div>

      <div className="page-header">
        <div>
          <h1 className="page-title">Conceptual Assessment & Mastery</h1>
          <p className="page-subtitle">
            Answer questions in your own words to demonstrate understanding. Receive detailed AI evaluations and track your concept mastery.
          </p>
        </div>
        <Link to={`/projects/${project.id}`} className="btn btn-secondary">
          ← Back to Project
        </Link>
      </div>

      {errorMsg && <div className="alert alert-danger" style={{ marginBottom: 20 }}>{errorMsg}</div>}

      {/* Grid: Left Column = Assessment, Right Column = Concept Mastery */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1fr)', gap: 24, alignItems: 'start' }}>
        
        {/* LEFT: ASSESSMENT SECTION */}
        <div>
          {readyMaterialsCount === 0 ? (
            <EmptyState
              icon="📝"
              title="Upload Study Materials First"
              description="Open-ended conceptual assessments are grounded directly in your uploaded PDF materials. Upload a document and wait for processing to complete."
              action={
                <Link to={`/projects/${project.id}`} className="btn btn-primary">
                  Go to Documents & Upload PDF
                </Link>
              }
            />
          ) : activeAssessment && currentQ ? (
            /* ACTIVE ASSESSMENT IN PROGRESS */
            <div className="assessment-container">
              <div className="assessment-header">
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    {activeAssessment.title}
                  </div>
                  <div style={{ fontSize: 16, fontWeight: 700, marginTop: 2 }}>
                    Question {currentQuestionIndex + 1} of {activeAssessment.questions.length}
                  </div>
                </div>
                <button onClick={() => setActiveAssessment(null)} className="btn btn-secondary btn-sm">
                  Exit Assessment
                </button>
              </div>

              <div className="assessment-body">
                {/* Concept and difficulty badge */}
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 14 }}>
                  <span className="quiz-concept-pill">
                    🏷️ {currentQ.concept}
                  </span>
                  <span className={`quiz-diff-badge ${currentQ.difficulty || 'medium'}`}>
                    {currentQ.difficulty || 'medium'}
                  </span>
                  {currentQ.source_metadata?.filename && (
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      📄 {currentQ.source_metadata.filename} (Page {currentQ.source_metadata.page})
                    </span>
                  )}
                </div>

                {/* Question text */}
                <h3 style={{ fontSize: 18, fontWeight: 700, lineHeight: 1.4, marginBottom: 20, color: 'var(--text-main)' }}>
                  {currentQ.question_text}
                </h3>

                {/* If already evaluated or response exists */}
                {existingResponseForQ || evaluation ? (
                  <div>
                    <div style={{ background: '#f8fafc', padding: 16, borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', marginBottom: 20 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
                        Your Response:
                      </div>
                      <p style={{ fontSize: 15, color: 'var(--text-main)', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                        {existingResponseForQ?.response_text || responseText}
                      </p>
                    </div>

                    {/* STRUCTURED EVALUATION CARD */}
                    <div className="evaluation-card">
                      <div className="evaluation-score-row">
                        <div>
                          <div style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                            AI Assessment Score
                          </div>
                          <div className="eval-score-badge">
                            {(existingResponseForQ || evaluation).score} / 100
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <span
                            style={{
                              fontSize: 12,
                              fontWeight: 700,
                              padding: '4px 12px',
                              borderRadius: 9999,
                              background: (existingResponseForQ || evaluation).score >= 70 ? 'var(--success-light)' : 'var(--warning-light)',
                              color: (existingResponseForQ || evaluation).score >= 70 ? 'var(--success)' : 'var(--warning)',
                            }}
                          >
                            {(existingResponseForQ || evaluation).score >= 70 ? 'Proficient' : 'Needs Review'}
                          </span>
                        </div>
                      </div>

                      {/* Understanding & Accuracy */}
                      <div style={{ marginBottom: 16 }}>
                        <div className="eval-section-title">Understanding & Accuracy</div>
                        <p style={{ fontSize: 14, color: 'var(--text-main)', marginTop: 4 }}>
                          {(existingResponseForQ || evaluation).understanding}
                        </p>
                        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
                          <strong>Accuracy:</strong> {(existingResponseForQ || evaluation).accuracy}
                        </p>
                      </div>

                      {/* Strengths */}
                      {(existingResponseForQ || evaluation).strengths?.length > 0 && (
                        <div style={{ marginBottom: 16 }}>
                          <div className="eval-section-title">Strengths Observed</div>
                          <div className="eval-pill-list">
                            {(existingResponseForQ || evaluation).strengths.map((s, i) => (
                              <span key={i} className="eval-pill-strength">
                                ✓ {s}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Missing Concepts */}
                      {(existingResponseForQ || evaluation).missing_concepts?.length > 0 && (
                        <div style={{ marginBottom: 16 }}>
                          <div className="eval-section-title">Missing Concepts / Topics to Include</div>
                          <div className="eval-pill-list">
                            {(existingResponseForQ || evaluation).missing_concepts.map((m, i) => (
                              <span key={i} className="eval-pill-missing">
                                ⚠️ {m}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Feedback */}
                      <div>
                        <div className="eval-section-title">Student-Friendly Feedback</div>
                        <p style={{ fontSize: 14, color: '#1e293b', background: '#ffffff', padding: 14, borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', lineHeight: 1.5, marginTop: 4 }}>
                          💬 {(existingResponseForQ || evaluation).feedback}
                        </p>
                      </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 24 }}>
                      <button onClick={handleNextQuestion} className="btn btn-primary">
                        {currentQuestionIndex + 1 < activeAssessment.questions.length ? 'Next Question ➔' : 'Complete Assessment 🏆'}
                      </button>
                    </div>
                  </div>
                ) : (
                  /* SUBMIT RESPONSE FORM */
                  <form onSubmit={handleSubmitResponse}>
                    <div className="form-group">
                      <label className="form-label" style={{ fontWeight: 600 }}>
                        Explain your answer in your own words:
                      </label>
                      <textarea
                        className="assessment-textarea"
                        placeholder="Write a clear, thoughtful explanation demonstrating your understanding of the concept and its relationships..."
                        value={responseText}
                        onChange={(e) => setResponseText(e.target.value)}
                        disabled={isSubmitting}
                        required
                      />
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                        <span>Focus on understanding and mechanisms, not simple keyword recall.</span>
                        <span>{responseText.length} characters</span>
                      </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 20 }}>
                      <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={isSubmitting || responseText.trim().length < 5}
                      >
                        {isSubmitting ? (
                          <>
                            <span className="spinner" style={{ width: 14, height: 14 }}></span> Evaluating with AI...
                          </>
                        ) : (
                          'Submit for AI Evaluation ➔'
                        )}
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          ) : (
            /* LAUNCHER & PAST ASSESSMENTS */
            <div>
              <div className="card" style={{ padding: 28, marginBottom: 28 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
                  <div>
                    <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-main)' }}>
                      Start Open-Ended Assessment
                    </h2>
                    <p style={{ color: 'var(--text-muted)', fontSize: 14, maxWidth: 500, marginTop: 4 }}>
                      Test your comprehension by explaining concepts in your own words. The AI evaluator provides structured feedback on your understanding, accuracy, strengths, and missing concepts.
                    </p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-muted)' }}>
                      <span>Questions:</span>
                      <select
                        className="form-input"
                        style={{ width: 'auto', padding: '6px 10px' }}
                        value={questionCount}
                        onChange={(e) => setQuestionCount(Number(e.target.value))}
                      >
                        <option value={1}>1 Question (Quick)</option>
                        <option value={2}>2 Questions</option>
                        <option value={3}>3 Questions (Standard)</option>
                        <option value={5}>5 Questions (Comprehensive)</option>
                      </select>
                    </div>
                    <button
                      onClick={handleStartAssessment}
                      className="btn btn-primary"
                      disabled={isStarting}
                    >
                      {isStarting ? (
                        <>
                          <span className="spinner" style={{ width: 14, height: 14 }}></span> Generating...
                        </>
                      ) : (
                        'Start Assessment 🚀'
                      )}
                    </button>
                  </div>
                </div>
              </div>

              {/* Past Assessments */}
              <div>
                <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>
                  Previous Assessments ({assessments.length})
                </h3>
                {assessments.length === 0 ? (
                  <div className="card" style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>
                    No assessments completed yet. Click <strong>Start Assessment</strong> above to test your understanding!
                  </div>
                ) : (
                  <table className="materials-table">
                    <thead>
                      <tr>
                        <th>Assessment</th>
                        <th>Status</th>
                        <th>Score</th>
                        <th>Date</th>
                        <th style={{ textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {assessments.map((a) => (
                        <tr key={a.id}>
                          <td>
                            <span style={{ fontWeight: 600 }}>{a.title} #{a.id}</span>
                          </td>
                          <td>
                            <span
                              style={{
                                fontSize: 11,
                                fontWeight: 700,
                                textTransform: 'uppercase',
                                padding: '3px 8px',
                                borderRadius: 9999,
                                background: a.status === 'completed' ? 'var(--success-light)' : 'var(--warning-light)',
                                color: a.status === 'completed' ? 'var(--success)' : 'var(--warning)',
                              }}
                            >
                              {a.status}
                            </span>
                          </td>
                          <td>
                            <span style={{ fontWeight: 600 }}>
                              {a.overall_score !== null ? `${Math.round(a.overall_score)}%` : 'In Progress'}
                            </span>
                          </td>
                          <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                            {formatDate(a.created_at)}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <button
                              onClick={() => handleReviewAssessment(a.id)}
                              className="btn btn-secondary btn-sm"
                            >
                              {a.status === 'completed' ? 'Review' : 'Continue'}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT: CONCEPT MASTERY DASHBOARD */}
        <div>
          <div className="mastery-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-main)' }}>
                  📊 Concept Mastery
                </h2>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  Estimated mastery based on quiz answers and assessment evaluations.
                </p>
              </div>
            </div>

            {/* Areas Needing Attention Alert */}
            {masteryData.areas_needing_attention && masteryData.areas_needing_attention.length > 0 && (
              <div className="attention-alert">
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700, fontSize: 13, color: '#92400e' }}>
                  <span>⚠️</span> Areas Needing Attention:
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                  {masteryData.areas_needing_attention.map((concept, idx) => (
                    <span key={idx} className="weak-concept-tag">
                      🏷️ {concept}
                    </span>
                  ))}
                </div>
                <p style={{ fontSize: 12, color: '#b45309', marginTop: 8 }}>
                  These concepts had lower scores or recent mistakes. Review the source notes or take focused assessments!
                </p>
              </div>
            )}

            {/* Concepts Progress List */}
            {masteryData.concepts.length === 0 ? (
              <div style={{ padding: '24px 10px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                <div style={{ fontSize: 24, marginBottom: 6 }}>📈</div>
                No concept evidence recorded yet.<br />
                Take an <strong>Adaptive Quiz</strong> or submit an <strong>Assessment</strong> to generate mastery estimates.
              </div>
            ) : (
              <div>
                {masteryData.concepts.map((c) => {
                  const score = Math.round(c.mastery_score);
                  const tier = score >= 75 ? 'high' : score >= 55 ? 'medium' : 'low';
                  return (
                    <div key={c.id} className="mastery-item">
                      <div className="mastery-info">
                        <div className="mastery-concept-name">{c.concept}</div>
                        <div className="mastery-meta">
                          {c.evidence_count} evidence item{c.evidence_count !== 1 ? 's' : ''} • {Math.round(c.confidence * 100)}% conf.
                        </div>
                      </div>

                      <div className="mastery-bar-container">
                        <div
                          className={`mastery-bar-fill ${tier}`}
                          style={{ width: `${score}%` }}
                        ></div>
                      </div>

                      <div className="mastery-score-text" style={{ color: tier === 'high' ? 'var(--success)' : tier === 'medium' ? 'var(--warning)' : 'var(--danger)' }}>
                        {score}%
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: 14, marginTop: 16, fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4 }}>
              💡 <em>Mastery estimates use a transparent moving average weighting 60% historical + 40% latest evidence. Confidence grows as you complete more checks.</em>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
