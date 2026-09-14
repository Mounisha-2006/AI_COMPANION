import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import { Modal } from '../components/Modal';

export function ProjectDetailPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [materials, setMaterials] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('materials'); // 'materials' | 'tutor' | 'quiz'

  // Upload modal state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef(null);

  // Material Replace & Delete state
  const [replacingMaterial, setReplacingMaterial] = useState(null);
  const [replaceFile, setReplaceFile] = useState(null);
  const [isReplacing, setIsReplacing] = useState(false);
  const [replaceError, setReplaceError] = useState('');
  const replaceFileInputRef = useRef(null);

  const [deletingMaterial, setDeletingMaterial] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState('');

  // AI Tutor state
  const [messages, setMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [chatError, setChatError] = useState('');
  const messagesEndRef = useRef(null);

  // Adaptive Quiz state
  const [quizzes, setQuizzes] = useState([]);
  const [activeQuiz, setActiveQuiz] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [selectedOption, setSelectedOption] = useState('');
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [answerFeedback, setAnswerFeedback] = useState(null); // { is_correct, correct_answer, feedback }
  const [nextQuestionData, setNextQuestionData] = useState(null);
  const [quizSummary, setQuizSummary] = useState(null);
  const [isStartingQuiz, setIsStartingQuiz] = useState(false);
  const [quizError, setQuizError] = useState('');
  const [quizQuestionCount, setQuizQuestionCount] = useState(5);
  const [quizScore, setQuizScore] = useState(0);
  const [questionsAnsweredCount, setQuestionsAnsweredCount] = useState(0);

  // Growth & Recommendations state
  const [growthData, setGrowthData] = useState(null);
  const [recommendationsData, setRecommendationsData] = useState(null);
  const [isLoadingGrowth, setIsLoadingGrowth] = useState(false);
  const [completingRecId, setCompletingRecId] = useState(null);

  // Project Analytics state
  const [projectAnalytics, setProjectAnalytics] = useState(null);
  const [isLoadingAnalytics, setIsLoadingAnalytics] = useState(false);
  const [analyticsError, setAnalyticsError] = useState('');

  const loadProjectAnalytics = async () => {
    setIsLoadingAnalytics(true);
    setAnalyticsError('');
    try {
      const data = await api.analytics.getProject(projectId);
      setProjectAnalytics(data);
    } catch (err) {
      console.error('Failed to load project analytics:', err);
      setAnalyticsError(err.message || 'Failed to load project analytics.');
    } finally {
      setIsLoadingAnalytics(false);
    }
  };

  const loadGrowthAndRecs = async () => {
    setIsLoadingGrowth(true);
    try {
      const [growth, recs] = await Promise.all([
        api.growth.get(projectId),
        api.recommendations.list(projectId),
      ]);
      setGrowthData(growth);
      setRecommendationsData(recs);
    } catch (err) {
      console.error('Failed to load growth or recommendations:', err);
    } finally {
      setIsLoadingGrowth(false);
    }
  };

  const handleCompleteRecommendation = async (recId) => {
    setCompletingRecId(recId);
    try {
      await api.recommendations.complete(projectId, recId);
      const updatedRecs = await api.recommendations.list(projectId);
      setRecommendationsData(updatedRecs);
    } catch (err) {
      alert(err.message || 'Failed to complete recommendation');
    } finally {
      setCompletingRecId(null);
    }
  };

  const loadProjectData = async () => {
    try {
      const [projData, matsData] = await Promise.all([
        api.projects.get(projectId),
        api.materials.list(projectId),
      ]);
      setProject(projData);
      setMaterials(matsData);
    } catch (err) {
      console.error('Failed to load project details:', err);
      if (err.status === 404) {
        navigate('/spaces');
      }
    } finally {
      setIsLoadingGrowth(false);
      setIsLoading(false);
    }
  };

  const loadTutorHistory = async () => {
    try {
      const history = await api.tutor.history(projectId);
      setMessages(history);
    } catch (err) {
      console.error('Failed to load tutor history:', err);
    }
  };

  const loadQuizzes = async () => {
    try {
      const list = await api.quiz.list(projectId);
      setQuizzes(list);
    } catch (err) {
      console.error('Failed to load quizzes:', err);
    }
  };

  useEffect(() => {
    loadProjectData();
    loadTutorHistory();
    loadQuizzes();
    loadGrowthAndRecs();
    loadProjectAnalytics();
  }, [projectId]);

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
        return `Created space "${meta.space_name || 'Space'}"`;
      case 'PROJECT_CREATED':
        return `Created project "${meta.project_name || 'Project'}"`;
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

  // Auto-polling for active background processing
  useEffect(() => {
    const hasPending = materials.some(
      (m) => m.status === 'queued' || m.status === 'processing'
    );
    if (!hasPending) return;

    const interval = setInterval(async () => {
      try {
        const updated = await api.materials.list(projectId);
        setMaterials(updated);
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [materials, projectId]);

  // Scroll to bottom of chat when messages change
  useEffect(() => {
    if (activeTab === 'tutor') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, activeTab, isThinking]);

  // Handle Upload
  const handleFileChange = (e) => {
    setUploadError('');
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
      setUploadError('Only PDF files are supported. Please select a valid .pdf file.');
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError('Please choose a PDF file to upload.');
      return;
    }

    setUploadError('');
    setIsUploading(true);

    try {
      await api.materials.upload(projectId, selectedFile);
      setSelectedFile(null);
      setIsUploadModalOpen(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
      setActionSuccessMsg('PDF uploaded! Processing chunks in the background.');
      setTimeout(() => setActionSuccessMsg(''), 4000);
      await loadProjectData();
    } catch (err) {
      setUploadError(err.message || 'Failed to upload material.');
    } finally {
      setIsUploading(false);
    }
  };

  // Handle Material Delete
  const handleDeleteMaterial = async () => {
    if (!deletingMaterial) return;
    setIsDeleting(true);
    try {
      await api.materials.delete(projectId, deletingMaterial.id);
      setDeletingMaterial(null);
      setActionSuccessMsg(`Deleted material "${deletingMaterial.filename}" and its chunks.`);
      setTimeout(() => setActionSuccessMsg(''), 4000);
      await loadProjectData();
      await loadQuizzes();
    } catch (err) {
      alert(err.message || 'Failed to delete material.');
    } finally {
      setIsDeleting(false);
    }
  };

  // Handle Material Replace
  const handleReplaceFileChange = (e) => {
    setReplaceError('');
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
      setReplaceError('Only PDF files are supported. Please select a valid .pdf file.');
      setReplaceFile(null);
      return;
    }

    setReplaceFile(file);
  };

  const handleReplaceMaterial = async (e) => {
    e.preventDefault();
    if (!replacingMaterial || !replaceFile) {
      setReplaceError('Please select a replacement PDF.');
      return;
    }

    setReplaceError('');
    setIsReplacing(true);

    try {
      await api.materials.replace(projectId, replacingMaterial.id, replaceFile);
      setReplacingMaterial(null);
      setReplaceFile(null);
      if (replaceFileInputRef.current) replaceFileInputRef.current.value = '';
      setActionSuccessMsg(`Replaced material with "${replaceFile.name}". Old chunks purged; re-indexing.`);
      setTimeout(() => setActionSuccessMsg(''), 4000);
      await loadProjectData();
    } catch (err) {
      setReplaceError(err.message || 'Failed to replace material.');
    } finally {
      setIsReplacing(false);
    }
  };

  // AI Tutor handlers
  const handleSendMessage = async (e) => {
    e.preventDefault();
    const query = chatInput.trim();
    if (!query || isThinking) return;

    setChatError('');
    setChatInput('');

    const tempUserMsg = {
      id: Date.now(),
      role: 'user',
      content: query,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsThinking(true);

    try {
      const response = await api.tutor.chat(projectId, query);
      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.answer,
        metadata: {
          sources: response.sources || [],
          grounded: response.grounded,
        },
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setChatError(err.message || 'Error getting response from AI Tutor.');
    } finally {
      setIsThinking(false);
    }
  };

  const handleClearChat = async () => {
    if (!window.confirm('Clear your AI Tutor conversation history for this project?')) {
      return;
    }
    try {
      await api.tutor.clearHistory(projectId);
      setMessages([]);
    } catch (err) {
      alert('Failed to clear conversation history: ' + err.message);
    }
  };

  // Adaptive Quiz Handlers
  const handleStartQuiz = async () => {
    setQuizError('');
    setIsStartingQuiz(true);
    setAnswerFeedback(null);
    setQuizSummary(null);
    setSelectedOption('');

    try {
      const quizRes = await api.quiz.start(projectId, quizQuestionCount);
      setActiveQuiz(quizRes);
      setCurrentQuestion(quizRes.current_question);
      setQuizScore(quizRes.score || 0);
      setQuestionsAnsweredCount(0);
      await loadQuizzes();
    } catch (err) {
      setQuizError(err.message || 'Failed to start quiz.');
    } finally {
      setIsStartingQuiz(false);
    }
  };

  const handleSubmitQuizAnswer = async (e) => {
    e.preventDefault();
    if (!selectedOption || !activeQuiz || !currentQuestion || isSubmittingAnswer) return;

    setIsSubmittingAnswer(true);
    setQuizError('');

    try {
      const result = await api.quiz.answer(
        projectId,
        activeQuiz.id,
        currentQuestion.id,
        selectedOption
      );

      setAnswerFeedback({
        is_correct: result.is_correct,
        correct_answer: result.correct_answer,
        feedback: result.feedback,
      });

      setQuizScore(result.current_score);
      setQuestionsAnsweredCount(result.total_answered);
      setNextQuestionData(result.next_question);

      if (result.is_completed) {
        setQuizSummary(result.summary);
      }
    } catch (err) {
      setQuizError(err.message || 'Failed to submit answer.');
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  const handleNextQuestion = () => {
    if (quizSummary) {
      // Quiz completed; clear active question to render summary screen
      setCurrentQuestion(null);
      setAnswerFeedback(null);
      setSelectedOption('');
      loadQuizzes();
    } else if (nextQuestionData) {
      setCurrentQuestion(nextQuestionData);
      setNextQuestionData(null);
      setAnswerFeedback(null);
      setSelectedOption('');
    }
  };

  const handleResumeOrReviewQuiz = async (quizId) => {
    try {
      const detail = await api.quiz.get(projectId, quizId);
      setActiveQuiz(detail);
      setQuizScore(detail.score);
      setQuestionsAnsweredCount(detail.answers ? detail.answers.length : 0);

      if (detail.status === 'completed') {
        setQuizSummary(detail.summary);
        setCurrentQuestion(null);
      } else {
        setCurrentQuestion(detail.current_question);
        setQuizSummary(null);
      }
      setAnswerFeedback(null);
      setSelectedOption('');
    } catch (err) {
      alert(err.message || 'Failed to load quiz details.');
    }
  };

  const handleQuitQuiz = () => {
    setActiveQuiz(null);
    setCurrentQuestion(null);
    setAnswerFeedback(null);
    setQuizSummary(null);
    setSelectedOption('');
    loadQuizzes();
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

  return (
    <div className="content-body">
      <div className="breadcrumbs">
        <Link to="/spaces">Spaces</Link>
        <span>/</span>
        <Link to={`/spaces/${project.space_id}`}>Space</Link>
        <span>/</span>
        <span>{project.name}</span>
      </div>

      <div className="page-header">
        <div>
          <h1 className="page-title">{project.name}</h1>
          <p className="page-subtitle">{project.description || 'No description provided.'}</p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <Link to={`/projects/${project.id}/assessment`} className="btn btn-secondary">
            <span>🎯</span> Assessment & Mastery
          </Link>
          <button onClick={() => setIsUploadModalOpen(true)} className="btn btn-primary">
            <span>⬆️</span> Upload PDF Material
          </button>
        </div>
      </div>

      {actionSuccessMsg && (
        <div className="alert alert-success" style={{ marginBottom: 16 }}>
          ✓ {actionSuccessMsg}
        </div>
      )}

      {/* Learning Goal Banner */}
      {project.learning_goal && (
        <div className="card" style={{ marginBottom: 24, borderLeft: '4px solid var(--primary)', background: '#faf5ff' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 18 }}>🎯</span>
            <span style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', color: 'var(--primary)', letterSpacing: 0.5 }}>
              Target Learning Goal
            </span>
          </div>
          <p style={{ fontSize: 15, fontWeight: 500, color: 'var(--text-main)', marginTop: 4 }}>
            {project.learning_goal}
          </p>
        </div>
      )}

      {/* Recommended Next Action Banner */}
      {recommendationsData?.next_action && (
        <div className="card next-action-card" style={{
          marginBottom: 24,
          background: 'linear-gradient(135deg, #eff6ff 0%, #f5f3ff 100%)',
          border: '1px solid #bfdbfe',
          boxShadow: '0 4px 14px rgba(59, 130, 246, 0.08)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 14 }}>
            <div style={{ flex: 1, minWidth: 280 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 20 }}>💡</span>
                <span style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', color: 'var(--primary)', letterSpacing: 0.6 }}>
                  Recommended Next Action
                </span>
                <span className={`badge ${recommendationsData.next_action.priority === 'high' ? 'badge-danger' : 'badge-primary'}`} style={{ fontSize: 11 }}>
                  {recommendationsData.next_action.priority === 'high' ? '⚡ High Priority' : '🎯 Next Focus'}
                </span>
                <span style={{ fontSize: 12, background: '#e0e7ff', color: '#3730a3', padding: '2px 8px', borderRadius: 999, fontWeight: 600 }}>
                  🏷️ {recommendationsData.next_action.concept}
                </span>
              </div>
              <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-main)', margin: '4px 0 6px', lineHeight: 1.4 }}>
                "{recommendationsData.next_action.recommendation}"
              </p>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
                <strong>Why:</strong> {recommendationsData.next_action.reason}
              </p>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              {recommendationsData.next_action.action_type === 'quiz' && (
                <button
                  onClick={() => setActiveTab('quiz')}
                  className="btn btn-primary"
                  style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                >
                  <span>📝</span> Start Practice Quiz
                </button>
              )}
              {recommendationsData.next_action.action_type === 'assessment' && (
                <Link
                  to={`/projects/${project.id}/assessment`}
                  className="btn btn-primary"
                  style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                >
                  <span>🎯</span> Start Assessment
                </Link>
              )}
              {recommendationsData.next_action.action_type === 'chat' && (
                <button
                  onClick={() => setActiveTab('tutor')}
                  className="btn btn-primary"
                  style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                >
                  <span>🤖</span> Ask AI Tutor
                </button>
              )}
              <button
                onClick={() => handleCompleteRecommendation(recommendationsData.next_action.id)}
                className="btn btn-secondary"
                disabled={completingRecId === recommendationsData.next_action.id}
                title="Mark this action as completed"
                style={{ padding: '8px 14px' }}
              >
                {completingRecId === recommendationsData.next_action.id ? '✓...' : '✓ Done'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="tabs-header">
        <button
          className={`tab-btn ${activeTab === 'materials' ? 'active' : ''}`}
          onClick={() => setActiveTab('materials')}
        >
          <span>📄</span> Study Materials ({materials.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'tutor' ? 'active' : ''}`}
          onClick={() => setActiveTab('tutor')}
        >
          <span>🤖</span> AI Tutor
          {readyMaterialsCount > 0 && (
            <span style={{ fontSize: 11, background: 'var(--success-light)', color: 'var(--success)', padding: '2px 6px', borderRadius: 999 }}>
              Ready
            </span>
          )}
        </button>
        <button
          className={`tab-btn ${activeTab === 'quiz' ? 'active' : ''}`}
          onClick={() => setActiveTab('quiz')}
        >
          <span>📝</span> Adaptive Quiz
          {quizzes.length > 0 && (
            <span style={{ fontSize: 11, background: 'var(--primary-light)', color: 'var(--primary)', padding: '2px 6px', borderRadius: 999 }}>
              {quizzes.length}
            </span>
          )}
        </button>
        <button
          className={`tab-btn ${activeTab === 'growth' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('growth');
            loadGrowthAndRecs();
          }}
        >
          <span>📈</span> Learning Growth
          {growthData?.concepts?.length > 0 && (
            <span style={{ fontSize: 11, background: '#dbeafe', color: '#1d4ed8', padding: '2px 6px', borderRadius: 999 }}>
              {growthData.concepts.length}
            </span>
          )}
        </button>
        <button
          className={`tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('analytics');
            loadProjectAnalytics();
          }}
        >
          <span>📊</span> Analytics
        </button>
        <Link
          to={`/projects/${project.id}/assessment`}
          className="tab-btn"
          style={{ textDecoration: 'none', color: 'inherit' }}
        >
          <span>🎯</span> Assessment & Mastery ➔
        </Link>
      </div>

      {/* TAB 1: MATERIALS */}
      {activeTab === 'materials' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700 }}>Project Documents</h2>
            {materials.some((m) => m.status === 'queued' || m.status === 'processing') && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--primary)' }}>
                <span className="spinner" style={{ width: 12, height: 12 }}></span>
                <span>Processing document chunks in background...</span>
              </div>
            )}
          </div>

          {materials.length === 0 ? (
            <EmptyState
              icon="📄"
              title="No Study Materials Yet"
              description="Upload PDF lecture notes, textbooks, or syllabus to enable semantic search, AI Tutor, and Adaptive Quizzes."
              action={
                <button onClick={() => setIsUploadModalOpen(true)} className="btn btn-primary">
                  Upload First PDF
                </button>
              }
            />
          ) : (
            <table className="materials-table">
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Status</th>
                  <th>Uploaded</th>
                  <th>Details / Error</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {materials.map((mat) => (
                  <tr key={mat.id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ fontSize: 20 }}>📄</span>
                        <span style={{ fontWeight: 600 }}>{mat.filename}</span>
                      </div>
                    </td>
                    <td>
                      <StatusBadge status={mat.status} />
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                      {formatDate(mat.created_at)}
                    </td>
                    <td>
                      {mat.status === 'failed' ? (
                        <span style={{ color: 'var(--danger)', fontSize: 12, fontWeight: 500 }}>
                          ⚠️ {mat.error_message || 'Processing failed.'}
                        </span>
                      ) : mat.status === 'ready' ? (
                        <span style={{ color: 'var(--success)', fontSize: 12, fontWeight: 500 }}>
                          ✓ Indexed for AI Tutor & Quiz
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                          Extracting text & chunks...
                        </span>
                      )}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="material-actions" style={{ justifyContent: 'flex-end' }}>
                        <button
                          onClick={() => {
                            setReplacingMaterial(mat);
                            setReplaceFile(null);
                            setReplaceError('');
                          }}
                          className="btn-replace"
                          title="Replace with updated PDF"
                        >
                          🔄 Replace
                        </button>
                        <button
                          onClick={() => setDeletingMaterial(mat)}
                          className="btn-danger-outline"
                          title="Delete PDF and associated chunks"
                        >
                          🗑️ Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* TAB 2: AI TUTOR */}
      {activeTab === 'tutor' && (
        <div className="tutor-container">
          <div className="tutor-header">
            <div>
              <div style={{ fontWeight: 700, fontSize: 16 }}>AI Study Tutor</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                Answers strictly grounded in <strong>{project.name}</strong> uploaded materials.
              </div>
            </div>
            {messages.length > 0 && (
              <button onClick={handleClearChat} className="btn btn-secondary btn-sm" title="Clear conversation">
                Clear Chat
              </button>
            )}
          </div>

          {readyMaterialsCount === 0 ? (
            <div style={{ padding: 40, textAlign: 'center' }}>
              <div style={{ fontSize: 36, marginBottom: 12 }}>📚</div>
              <h3 style={{ fontSize: 17, fontWeight: 700 }}>No Ready Materials Found</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: 14, maxWidth: 450, margin: '8px auto 20px' }}>
                The AI Tutor requires at least one processed PDF in this project to provide grounded answers and citations.
              </p>
              <button onClick={() => { setActiveTab('materials'); setIsUploadModalOpen(true); }} className="btn btn-primary">
                Upload a PDF Document
              </button>
            </div>
          ) : (
            <>
              <div className="tutor-messages">
                {messages.length === 0 && (
                  <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--text-muted)' }}>
                    <div style={{ fontSize: 32, marginBottom: 8 }}>💡</div>
                    <div style={{ fontWeight: 600, fontSize: 16, color: 'var(--text-main)' }}>
                      Ask your AI Tutor anything about this project!
                    </div>
                    <p style={{ fontSize: 13, marginTop: 4 }}>
                      Answers will cite the exact page numbers from your uploaded PDFs.
                    </p>
                    <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 18, flexWrap: 'wrap' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => setChatInput('What is the main concept explained in this document?')}
                      >
                        "What is the main concept explained?"
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => setChatInput('Summarize the key definitions and formulas.')}
                      >
                        "Summarize key definitions"
                      </button>
                    </div>
                  </div>
                )}

                {messages.map((msg) => (
                  <div key={msg.id} className={`message-item ${msg.role}`}>
                    <div className="message-sender">
                      {msg.role === 'user' ? '👤 You' : '🤖 AI Tutor'}
                      {msg.role === 'assistant' && msg.metadata?.grounded && (
                        <span className="grounded-badge">✓ Grounded in Document</span>
                      )}
                    </div>
                    <div className="message-bubble">{msg.content}</div>

                    {/* Citations */}
                    {msg.role === 'assistant' && msg.metadata?.sources && msg.metadata.sources.length > 0 && (
                      <div className="citations-box">
                        <div className="citations-title">
                          <span>📄 Sources & Citations:</span>
                        </div>
                        <div className="citations-list">
                          {msg.metadata.sources.map((src, i) => (
                            <span key={i} className="citation-chip">
                              📄 {src.filename} — Page {src.page}{src.visual_type ? ` (${src.visual_type.charAt(0).toUpperCase() + src.visual_type.slice(1)})` : ''}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {isThinking && (
                  <div className="message-item assistant">
                    <div className="message-sender">🤖 AI Tutor</div>
                    <div className="message-bubble" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className="spinner" style={{ width: 14, height: 14 }}></span>
                      <span>Searching project documents and formulating answer...</span>
                    </div>
                  </div>
                )}

                {chatError && <div className="alert alert-danger">{chatError}</div>}
                <div ref={messagesEndRef} />
              </div>

              {/* Chat Input */}
              <form className="tutor-input-bar" onSubmit={handleSendMessage}>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Ask a question based on your uploaded materials..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  disabled={isThinking}
                />
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isThinking || !chatInput.trim()}
                >
                  {isThinking ? <span className="spinner"></span> : 'Send ✈️'}
                </button>
              </form>
            </>
          )}
        </div>
      )}

      {/* TAB 3: ADAPTIVE QUIZ */}
      {activeTab === 'quiz' && (
        <div>
          {readyMaterialsCount === 0 ? (
            <EmptyState
              icon="📝"
              title="Upload Study Material First"
              description="Adaptive quizzes are generated directly from your project's uploaded PDFs. Upload a document and wait for processing to complete."
              action={
                <button onClick={() => { setActiveTab('materials'); setIsUploadModalOpen(true); }} className="btn btn-primary">
                  Upload PDF Material
                </button>
              }
            />
          ) : activeQuiz && currentQuestion ? (
            /* VIEW 1: ACTIVE QUIZ IN PROGRESS */
            <div className="quiz-container">
              <div className="quiz-card-header">
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    Adaptive Knowledge Check
                  </div>
                  <div style={{ fontSize: 15, fontWeight: 700, marginTop: 2 }}>
                    Question {questionsAnsweredCount + 1} of {activeQuiz.total_questions}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>
                    Score: <span style={{ color: 'var(--primary)' }}>{quizScore}</span> / {questionsAnsweredCount}
                  </div>
                  <button onClick={handleQuitQuiz} className="btn btn-secondary btn-sm">
                    Exit Quiz
                  </button>
                </div>
              </div>

              {/* Progress bar */}
              <div className="quiz-progress-track">
                <div
                  className="quiz-progress-fill"
                  style={{ width: `${(questionsAnsweredCount / activeQuiz.total_questions) * 100}%` }}
                ></div>
              </div>

              <div className="quiz-question-body">
                {/* Concept and Difficulty Badges */}
                <div className="quiz-badges-row">
                  <span className="quiz-concept-pill">
                    <span>🏷️</span> {currentQuestion.concept}
                  </span>
                  <span className={`quiz-diff-badge ${currentQuestion.difficulty || 'medium'}`}>
                    Difficulty: {currentQuestion.difficulty || 'medium'}
                  </span>
                </div>

                {/* Question text */}
                <div className="quiz-question-text">
                  {currentQuestion.question_text}
                </div>

                {/* Options List */}
                <form onSubmit={handleSubmitQuizAnswer}>
                  <div className="quiz-options-grid">
                    {currentQuestion.options.map((opt, index) => {
                      const isSelected = selectedOption === opt;
                      return (
                        <label
                          key={index}
                          className={`quiz-option-label ${isSelected ? 'selected' : ''}`}
                        >
                          <input
                            type="radio"
                            name="quiz-option"
                            value={opt}
                            checked={isSelected}
                            onChange={() => !answerFeedback && setSelectedOption(opt)}
                            disabled={answerFeedback !== null || isSubmittingAnswer}
                            className="quiz-option-radio"
                          />
                          <span style={{ fontSize: 15, lineHeight: 1.4, color: 'var(--text-main)' }}>
                            {opt}
                          </span>
                        </label>
                      );
                    })}
                  </div>

                  {quizError && <div className="alert alert-danger" style={{ marginBottom: 16 }}>{quizError}</div>}

                  {/* Immediate Feedback Box */}
                  {answerFeedback && (
                    <div className={`quiz-feedback-box ${answerFeedback.is_correct ? 'correct' : 'incorrect'}`}>
                      <div className="quiz-feedback-title">
                        {answerFeedback.is_correct ? (
                          <><span>✓</span> Correct! Excellent reasoning.</>
                        ) : (
                          <><span>✗</span> Incorrect.</>
                        )}
                      </div>
                      <div style={{ fontSize: 14 }}>
                        {answerFeedback.feedback}
                      </div>
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 24 }}>
                    {!answerFeedback ? (
                      <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={!selectedOption || isSubmittingAnswer}
                      >
                        {isSubmittingAnswer ? (
                          <>
                            <span className="spinner" style={{ width: 14, height: 14 }}></span> Evaluating...
                          </>
                        ) : (
                          'Submit Answer ➔'
                        )}
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={handleNextQuestion}
                        className="btn btn-primary"
                      >
                        {quizSummary ? 'View Final Results 🏆' : 'Next Question ➔'}
                      </button>
                    )}
                  </div>
                </form>
              </div>
            </div>
          ) : quizSummary ? (
            /* VIEW 2: QUIZ COMPLETED SUMMARY */
            <div className="quiz-container">
              <div className="quiz-summary-container">
                <div style={{ fontSize: 50, marginBottom: 8 }}>🏆</div>
                <h2 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-main)' }}>
                  Quiz Completed!
                </h2>
                <p style={{ color: 'var(--text-muted)', fontSize: 15, marginTop: 4 }}>
                  Here is how you performed on this adaptive assessment:
                </p>

                <div style={{ margin: '24px 0' }}>
                  <div className="quiz-score-badge">
                    {quizSummary.score} / {quizSummary.total_questions}
                  </div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-main)' }}>
                    {quizSummary.percentage}% Accuracy
                  </div>
                </div>

                {/* Concepts needing attention */}
                {quizSummary.weak_concepts && quizSummary.weak_concepts.length > 0 ? (
                  <div className="weak-concepts-box">
                    <div style={{ fontWeight: 700, fontSize: 14, color: '#92400e', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span>⚠️</span> Concepts Needing Attention:
                    </div>
                    <p style={{ fontSize: 13, color: '#b45309', marginTop: 4 }}>
                      Based on your incorrect responses, we recommend reviewing these specific topics in your project materials:
                    </p>
                    <div className="weak-concepts-tags">
                      {quizSummary.weak_concepts.map((concept, i) => (
                        <span key={i} className="weak-concept-tag">
                          🏷️ {concept}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="alert alert-success" style={{ maxWidth: 540, margin: '24px auto', textAlign: 'left' }}>
                    <div style={{ fontWeight: 700 }}>🎉 Perfect Mastery!</div>
                    <div style={{ fontSize: 13, marginTop: 2 }}>
                      You answered all questions correctly across every tested concept in this document!
                    </div>
                  </div>
                )}

                <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 28 }}>
                  <button onClick={handleStartQuiz} className="btn btn-primary">
                    Take Another Adaptive Quiz 🚀
                  </button>
                  <button onClick={handleQuitQuiz} className="btn btn-secondary">
                    View Previous Attempts
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* VIEW 3: QUIZ LAUNCHER & PAST ATTEMPTS */
            <div>
              <div className="card" style={{ marginBottom: 28, padding: 28 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
                  <div>
                    <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-main)' }}>
                      Adaptive Knowledge Assessment
                    </h2>
                    <p style={{ color: 'var(--text-muted)', fontSize: 14, maxWidth: 550, marginTop: 4 }}>
                      Assess your understanding of <strong>{project.name}</strong>. Questions are generated dynamically from your uploaded materials and adapt in difficulty as you answer.
                    </p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-muted)' }}>
                      <span>Questions:</span>
                      <select
                        className="form-input"
                        style={{ width: 'auto', padding: '6px 10px' }}
                        value={quizQuestionCount}
                        onChange={(e) => setQuizQuestionCount(Number(e.target.value))}
                      >
                        <option value={3}>3 Questions (Quick)</option>
                        <option value={5}>5 Questions (Standard)</option>
                        <option value={10}>10 Questions (In-depth)</option>
                      </select>
                    </div>
                    <button
                      onClick={handleStartQuiz}
                      className="btn btn-primary"
                      disabled={isStartingQuiz}
                    >
                      {isStartingQuiz ? (
                        <>
                          <span className="spinner" style={{ width: 14, height: 14 }}></span> Generating Quiz...
                        </>
                      ) : (
                        'Start Adaptive Quiz 🚀'
                      )}
                    </button>
                  </div>
                </div>

                {quizError && <div className="alert alert-danger" style={{ marginTop: 16 }}>{quizError}</div>}
              </div>

              {/* Previous Quizzes List */}
              <div style={{ marginTop: 24 }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>
                  Previous Quiz Attempts ({quizzes.length})
                </h3>

                {quizzes.length === 0 ? (
                  <div className="card" style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>
                    No quiz attempts yet for this project. Click <strong>Start Adaptive Quiz</strong> above to test your knowledge!
                  </div>
                ) : (
                  <table className="materials-table">
                    <thead>
                      <tr>
                        <th>Quiz ID</th>
                        <th>Status</th>
                        <th>Score</th>
                        <th>Date</th>
                        <th style={{ textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {quizzes.map((q) => {
                        const pct = q.total_questions > 0 ? Math.round((q.score / q.total_questions) * 100) : 0;
                        return (
                          <tr key={q.id}>
                            <td>
                              <span style={{ fontWeight: 600 }}>Quiz #{q.id}</span>
                            </td>
                            <td>
                              <span
                                style={{
                                  fontSize: 11,
                                  fontWeight: 700,
                                  textTransform: 'uppercase',
                                  padding: '3px 8px',
                                  borderRadius: 9999,
                                  background: q.status === 'completed' ? 'var(--success-light)' : 'var(--warning-light)',
                                  color: q.status === 'completed' ? 'var(--success)' : 'var(--warning)',
                                }}
                              >
                                {q.status === 'completed' ? 'Completed' : 'In Progress'}
                              </span>
                            </td>
                            <td>
                              <span style={{ fontWeight: 600 }}>
                                {q.score} / {q.total_questions} ({pct}%)
                              </span>
                            </td>
                            <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                              {formatDate(q.started_at || q.created_at)}
                            </td>
                            <td style={{ textAlign: 'right' }}>
                              <button
                                onClick={() => handleResumeOrReviewQuiz(q.id)}
                                className="btn btn-secondary btn-sm"
                              >
                                {q.status === 'completed' ? 'Review' : 'Resume'}
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: LEARNING GROWTH & RECOMMENDATIONS */}
      {activeTab === 'growth' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div>
              <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Learning Growth & Recommendations</h2>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '4px 0 0' }}>
                Track conceptual progress, trajectory over time, and AI-directed next actions.
              </p>
            </div>
            <button
              onClick={loadGrowthAndRecs}
              className="btn btn-secondary btn-sm"
              disabled={isLoadingGrowth}
            >
              {isLoadingGrowth ? 'Analyzing...' : '🔄 Refresh Analysis'}
            </button>
          </div>

          {isLoadingGrowth && !growthData ? (
            <div style={{ textAlign: 'center', padding: 60 }}>
              <span className="spinner"></span>
              <p style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 12 }}>Computing growth trajectory...</p>
            </div>
          ) : !growthData || growthData.concepts.length === 0 ? (
            <EmptyState
              icon="📈"
              title="No Learning Growth Data Yet"
              description="Complete quizzes or open-ended assessments to establish mastery baselines and begin tracking learning growth."
              action={
                <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
                  <button onClick={() => setActiveTab('quiz')} className="btn btn-primary">
                    Start Adaptive Quiz
                  </button>
                  <Link to={`/projects/${project.id}/assessment`} className="btn btn-secondary">
                    Open-Ended Assessment
                  </Link>
                </div>
              }
            />
          ) : (
            <div>
              {/* Overall Progress Summary Card */}
              <div className="card" style={{ marginBottom: 24, padding: 24 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
                  <div>
                    <span style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: 0.5 }}>
                      Overall Project Progress
                    </span>
                    <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--primary)', marginTop: 4 }}>
                      {growthData.overall_progress}%
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                    <div style={{
                      padding: '10px 16px',
                      background: 'var(--success-light)',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid #bbf7d0',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--success)' }}>
                        {growthData.summary.improving_areas.length}
                      </div>
                      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--success)', textTransform: 'uppercase' }}>
                        Improving
                      </div>
                    </div>

                    <div style={{
                      padding: '10px 16px',
                      background: '#eff6ff',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid #bfdbfe',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: 20, fontWeight: 700, color: '#1d4ed8' }}>
                        {growthData.summary.stable_areas.length}
                      </div>
                      <div style={{ fontSize: 11, fontWeight: 600, color: '#1d4ed8', textTransform: 'uppercase' }}>
                        Stable
                      </div>
                    </div>

                    <div style={{
                      padding: '10px 16px',
                      background: 'var(--danger-light)',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid #fecaca',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--danger)' }}>
                        {growthData.summary.areas_requiring_attention.length}
                      </div>
                      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--danger)', textTransform: 'uppercase' }}>
                        Needs Attention
                      </div>
                    </div>
                  </div>
                </div>

                {/* Progress bar */}
                <div style={{
                  width: '100%',
                  height: 10,
                  background: '#e2e8f0',
                  borderRadius: 999,
                  overflow: 'hidden',
                  marginTop: 16
                }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${growthData.overall_progress}%`,
                      background: 'linear-gradient(90deg, #3b82f6 0%, #10b981 100%)',
                      borderRadius: 999,
                      transition: 'width 0.4s ease'
                    }}
                  />
                </div>
              </div>

              {/* Categorized Concept Columns */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                gap: 16,
                marginBottom: 28
              }}>
                {/* IMPROVING */}
                <div className="card" style={{ borderTop: '4px solid var(--success)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: 'var(--success)' }}>
                      🚀 Improving Areas
                    </h3>
                    <span style={{ fontSize: 12, fontWeight: 700, background: 'var(--success-light)', color: 'var(--success)', padding: '2px 8px', borderRadius: 999 }}>
                      {growthData.summary.improving_areas.length}
                    </span>
                  </div>
                  {growthData.concepts.filter(c => c.status === 'Improving').length === 0 ? (
                    <p style={{ fontSize: 13, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      No concepts currently in improving status.
                    </p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {growthData.concepts.filter(c => c.status === 'Improving').map(c => (
                        <div key={c.concept} style={{
                          padding: '10px 12px',
                          background: '#f8fafc',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border)'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontWeight: 600, fontSize: 14 }}>{c.concept}</span>
                            <span style={{
                              fontWeight: 700,
                              fontSize: 12,
                              color: 'var(--success)',
                              background: 'var(--success-light)',
                              padding: '2px 6px',
                              borderRadius: 4
                            }}>
                              +{c.change}%
                            </span>
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                            Previous: {c.previous_mastery}% ➔ Current: <strong>{c.current_mastery}%</strong>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* STABLE */}
                <div className="card" style={{ borderTop: '4px solid #3b82f6' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: '#1d4ed8' }}>
                      ⚖️ Stable Areas
                    </h3>
                    <span style={{ fontSize: 12, fontWeight: 700, background: '#eff6ff', color: '#1d4ed8', padding: '2px 8px', borderRadius: 999 }}>
                      {growthData.summary.stable_areas.length}
                    </span>
                  </div>
                  {growthData.concepts.filter(c => c.status === 'Stable').length === 0 ? (
                    <p style={{ fontSize: 13, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      No concepts currently in stable status.
                    </p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {growthData.concepts.filter(c => c.status === 'Stable').map(c => (
                        <div key={c.concept} style={{
                          padding: '10px 12px',
                          background: '#f8fafc',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border)'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontWeight: 600, fontSize: 14 }}>{c.concept}</span>
                            <span style={{
                              fontWeight: 700,
                              fontSize: 12,
                              color: '#1d4ed8',
                              background: '#eff6ff',
                              padding: '2px 6px',
                              borderRadius: 4
                            }}>
                              {c.change >= 0 ? `+${c.change}%` : `${c.change}%`}
                            </span>
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                            Previous: {c.previous_mastery}% ➔ Current: <strong>{c.current_mastery}%</strong>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* NEEDS ATTENTION */}
                <div className="card" style={{ borderTop: '4px solid var(--danger)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: 'var(--danger)' }}>
                      ⚠️ Needs Attention
                    </h3>
                    <span style={{ fontSize: 12, fontWeight: 700, background: 'var(--danger-light)', color: 'var(--danger)', padding: '2px 8px', borderRadius: 999 }}>
                      {growthData.summary.areas_requiring_attention.length}
                    </span>
                  </div>
                  {growthData.concepts.filter(c => c.status === 'Needs Attention').length === 0 ? (
                    <p style={{ fontSize: 13, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      Great job! No concepts currently need urgent attention.
                    </p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {growthData.concepts.filter(c => c.status === 'Needs Attention').map(c => (
                        <div key={c.concept} style={{
                          padding: '10px 12px',
                          background: '#fff5f5',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid #fed7d7'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--danger)' }}>{c.concept}</span>
                            <span style={{
                              fontWeight: 700,
                              fontSize: 12,
                              color: 'var(--danger)',
                              background: 'var(--danger-light)',
                              padding: '2px 6px',
                              borderRadius: 4
                            }}>
                              {c.change > 0 ? `+${c.change}%` : `${c.change}%`}
                            </span>
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                            Previous: {c.previous_mastery}% ➔ Current: <strong>{c.current_mastery}%</strong>
                            {c.recent_mistakes > 0 && (
                              <span style={{ color: 'var(--danger)', marginLeft: 8 }}>
                                ({c.recent_mistakes} recent {c.recent_mistakes === 1 ? 'mistake' : 'mistakes'})
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Concept Growth Comparison Table */}
              <div className="card" style={{ marginBottom: 28 }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 14 }}>
                  Detailed Concept Growth Matrix
                </h3>
                <div style={{ overflowX: 'auto' }}>
                  <table className="table" style={{ width: '100%' }}>
                    <thead>
                      <tr>
                        <th>Concept</th>
                        <th>Previous Mastery</th>
                        <th>Current Mastery</th>
                        <th>Change</th>
                        <th>Status</th>
                        <th style={{ textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {growthData.concepts.map((c) => {
                        return (
                          <tr key={c.concept}>
                            <td style={{ fontWeight: 600 }}>{c.concept}</td>
                            <td>{c.previous_mastery}%</td>
                            <td style={{ fontWeight: 700 }}>{c.current_mastery}%</td>
                            <td>
                              <span style={{
                                fontWeight: 700,
                                color: c.change > 0 ? 'var(--success)' : c.change < 0 ? 'var(--danger)' : 'var(--text-muted)'
                              }}>
                                {c.change > 0 ? `+${c.change}%` : `${c.change}%`}
                              </span>
                            </td>
                            <td>
                              <span style={{
                                fontSize: 11,
                                fontWeight: 700,
                                textTransform: 'uppercase',
                                padding: '3px 8px',
                                borderRadius: 9999,
                                background:
                                  c.status === 'Improving'
                                    ? 'var(--success-light)'
                                    : c.status === 'Needs Attention'
                                    ? 'var(--danger-light)'
                                    : '#eff6ff',
                                color:
                                  c.status === 'Improving'
                                    ? 'var(--success)'
                                    : c.status === 'Needs Attention'
                                    ? 'var(--danger)'
                                    : '#1d4ed8',
                              }}>
                                {c.status}
                              </span>
                            </td>
                            <td style={{ textAlign: 'right' }}>
                              <button
                                onClick={() => setActiveTab('quiz')}
                                className="btn btn-secondary btn-sm"
                                style={{ marginRight: 6 }}
                              >
                                Quiz
                              </button>
                              <Link
                                to={`/projects/${project.id}/assessment`}
                                className="btn btn-primary btn-sm"
                              >
                                Assess
                              </Link>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* All Recommendations Section */}
              {recommendationsData?.recommendations?.length > 0 && (
                <div className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <div>
                      <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>
                        Learning Action Plan
                      </h3>
                      <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '4px 0 0' }}>
                        Personalized guidance answering "What should I do next?"
                      </p>
                    </div>
                    <span style={{ fontSize: 12, background: 'var(--primary-light)', color: 'var(--primary)', padding: '3px 8px', borderRadius: 999, fontWeight: 600 }}>
                      {recommendationsData.pending_count} pending
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {recommendationsData.recommendations.map((rec) => {
                      const isDone = rec.completed_at !== null;
                      return (
                        <div
                          key={rec.id}
                          style={{
                            padding: '14px 16px',
                            background: isDone ? '#f8fafc' : '#fff',
                            borderRadius: 'var(--radius-sm)',
                            border: `1px solid ${isDone ? 'var(--border)' : rec.priority === 'high' ? '#fecaca' : '#bfdbfe'}`,
                            opacity: isDone ? 0.65 : 1,
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'flex-start',
                            flexWrap: 'wrap',
                            gap: 12
                          }}
                        >
                          <div style={{ flex: 1, minWidth: 260 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                              <span className={`badge ${rec.priority === 'high' ? 'badge-danger' : 'badge-primary'}`} style={{ fontSize: 10 }}>
                                {rec.priority === 'high' ? '⚡ High' : '🎯 Regular'}
                              </span>
                              <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--primary)' }}>
                                🏷️ {rec.concept}
                              </span>
                              {isDone && (
                                <span style={{ fontSize: 11, color: 'var(--success)', fontWeight: 600 }}>
                                  ✓ Completed
                                </span>
                              )}
                            </div>
                            <p style={{ fontSize: 14, fontWeight: isDone ? 400 : 600, color: 'var(--text-main)', margin: '4px 0' }}>
                              "{rec.recommendation}"
                            </p>
                            <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
                              <strong>Reason:</strong> {rec.reason}
                            </p>
                          </div>

                          {!isDone && (
                            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                              {rec.action_type === 'quiz' && (
                                <button
                                  onClick={() => setActiveTab('quiz')}
                                  className="btn btn-secondary btn-sm"
                                >
                                  Practice Quiz
                                </button>
                              )}
                              {rec.action_type === 'assessment' && (
                                <Link
                                  to={`/projects/${project.id}/assessment`}
                                  className="btn btn-secondary btn-sm"
                                >
                                  Take Assessment
                                </Link>
                              )}
                              {rec.action_type === 'chat' && (
                                <button
                                  onClick={() => setActiveTab('tutor')}
                                  className="btn btn-secondary btn-sm"
                                >
                                  Ask AI Tutor
                                </button>
                              )}
                              <button
                                onClick={() => handleCompleteRecommendation(rec.id)}
                                className="btn btn-primary btn-sm"
                                disabled={completingRecId === rec.id}
                              >
                                {completingRecId === rec.id ? 'Saving...' : 'Mark Done'}
                              </button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 5: PROJECT ANALYTICS */}
      {activeTab === 'analytics' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div>
              <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Project Learning Analytics</h2>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '4px 0 0' }}>
                Activity metrics, performance insights, and AI interactions for {project.name}.
              </p>
            </div>
            <button
              onClick={loadProjectAnalytics}
              className="btn btn-secondary btn-sm"
              disabled={isLoadingAnalytics}
            >
              {isLoadingAnalytics ? 'Updating...' : '🔄 Refresh Analytics'}
            </button>
          </div>

          {isLoadingAnalytics && !projectAnalytics ? (
            <div style={{ textAlign: 'center', padding: 60 }}>
              <span className="spinner"></span>
              <p style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 12 }}>Computing project analytics...</p>
            </div>
          ) : analyticsError ? (
            <div className="card" style={{ padding: 24, textAlign: 'center', borderColor: 'var(--danger)' }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>⚠️</div>
              <div style={{ color: 'var(--danger)', fontWeight: 600, marginBottom: 12 }}>{analyticsError}</div>
              <button onClick={loadProjectAnalytics} className="btn btn-primary btn-sm">Retry</button>
            </div>
          ) : !projectAnalytics ? (
            <EmptyState
              icon="📊"
              title="No Analytics Available"
              description="Interact with the study tutor, take quizzes, or upload materials to populate project analytics."
            />
          ) : (
            <div>
              {/* Activity & Performance Key Metric Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 24 }}>
                {/* Current Mastery */}
                <div className="card" style={{ padding: 18 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Current Mastery</div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: projectAnalytics.performance.current_mastery >= 75 ? 'var(--success)' : 'var(--primary)', marginTop: 4 }}>
                    {projectAnalytics.performance.current_mastery}%
                  </div>
                  <div style={{ width: '100%', background: 'var(--border)', height: 6, borderRadius: 3, marginTop: 8, overflow: 'hidden' }}>
                    <div style={{ width: `${Math.min(projectAnalytics.performance.current_mastery, 100)}%`, height: '100%', background: projectAnalytics.performance.current_mastery >= 75 ? 'var(--success)' : 'var(--primary)', borderRadius: 3 }} />
                  </div>
                </div>

                {/* Quiz Accuracy */}
                <div className="card" style={{ padding: 18 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Quiz Accuracy</div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-main)', marginTop: 4 }}>
                    {projectAnalytics.performance.quiz_accuracy}%
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                    {projectAnalytics.activity.quiz_attempts} quiz attempts
                  </div>
                </div>

                {/* Questions Answered */}
                <div className="card" style={{ padding: 18 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Questions Answered</div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-main)', marginTop: 4 }}>
                    {projectAnalytics.activity.questions_answered}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                    Quizzes & Assessments
                  </div>
                </div>

                {/* Tutor Questions */}
                <div className="card" style={{ padding: 18 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Tutor Questions</div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-main)', marginTop: 4 }}>
                    {projectAnalytics.activity.tutor_questions}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                    AI Tutor interactions
                  </div>
                </div>

                {/* Learning Sessions */}
                <div className="card" style={{ padding: 18 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Active Days</div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-main)', marginTop: 4 }}>
                    {projectAnalytics.activity.learning_sessions}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                    {projectAnalytics.activity.total_events} total events
                  </div>
                </div>
              </div>

              {/* Concepts Performance Breakdown */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20, marginBottom: 24 }}>
                {/* Mastered Concepts */}
                <div className="card" style={{ padding: 20, borderTop: '4px solid var(--success)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: '#065f46' }}>
                      🌟 Mastered Concepts ({projectAnalytics.performance.concepts_mastered_count})
                    </h3>
                  </div>
                  {projectAnalytics.performance.concepts_mastered?.length > 0 ? (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {projectAnalytics.performance.concepts_mastered.map((c) => (
                        <span key={c} className="badge" style={{ background: 'var(--success-light)', color: 'var(--success)', padding: '4px 10px', borderRadius: 6, fontWeight: 600 }}>
                          ✓ {c}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
                      No concepts reached 75%+ mastery yet. Take quizzes and assessments to level up!
                    </p>
                  )}
                </div>

                {/* Concepts Needing Attention */}
                <div className="card" style={{ padding: 20, borderTop: '4px solid var(--warning)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: '#92400e' }}>
                      ⚠️ Requiring Attention ({projectAnalytics.performance.concepts_needing_attention_count})
                    </h3>
                  </div>
                  {projectAnalytics.performance.concepts_needing_attention?.length > 0 ? (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {projectAnalytics.performance.concepts_needing_attention.map((c) => (
                        <span key={c} className="badge" style={{ background: 'var(--warning-light)', color: '#b45309', padding: '4px 10px', borderRadius: 6, fontWeight: 600 }}>
                          ! {c}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
                      Great job! No concepts currently flagged for mistakes or low scores.
                    </p>
                  )}
                </div>
              </div>

              {/* 14-Day Activity Timeline & AI Activity */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20, marginBottom: 24 }}>
                {/* Timeline */}
                <div className="card" style={{ padding: 20 }}>
                  <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>Learning Activity (Last 14 Days)</h3>
                  <div style={{ display: 'flex', alignItems: 'flex-end', height: 120, gap: 6, paddingTop: 12 }}>
                    {projectAnalytics.growth.activity_over_time?.map((pt, idx) => {
                      const maxVal = Math.max(...(projectAnalytics.growth.activity_over_time?.map(p => p.count) || [1]), 1);
                      const heightPercent = pt.count > 0 ? Math.max((pt.count / maxVal) * 100, 15) : 4;
                      const isToday = idx === (projectAnalytics.growth.activity_over_time.length - 1);
                      return (
                        <div key={pt.date} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }} title={`${pt.date}: ${pt.count} events`}>
                          <span style={{ fontSize: 10, color: pt.count > 0 ? 'var(--text-main)' : 'transparent', fontWeight: 600, marginBottom: 2 }}>
                            {pt.count > 0 ? pt.count : ''}
                          </span>
                          <div style={{ width: '100%', height: `${heightPercent}%`, background: isToday ? 'var(--primary)' : pt.count > 0 ? '#818cf8' : 'var(--border)', borderRadius: '3px 3px 0 0' }} />
                          <span style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 4 }}>
                            {pt.date.slice(5)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* AI Activity Summary */}
                <div className="card" style={{ padding: 20 }}>
                  <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>AI Activity & Contributions</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--bg-main)', borderRadius: 6, fontSize: 13 }}>
                      <span>Tutor Questions Answered:</span>
                      <strong style={{ color: 'var(--primary)' }}>{projectAnalytics.ai_activity.tutor_interactions}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--bg-main)', borderRadius: 6, fontSize: 13 }}>
                      <span>AI-Generated Assessments:</span>
                      <strong>{projectAnalytics.ai_activity.ai_generated_assessments}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--bg-main)', borderRadius: 6, fontSize: 13 }}>
                      <span>AI Student Evaluations:</span>
                      <strong>{projectAnalytics.ai_activity.ai_evaluations}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--bg-main)', borderRadius: 6, fontSize: 13 }}>
                      <span>Study Recommendations:</span>
                      <strong>{projectAnalytics.ai_activity.recommendations_generated}</strong>
                    </div>
                  </div>
                </div>
              </div>

              {/* Recent Activity for this Project */}
              <div className="card" style={{ padding: 20 }}>
                <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>Recent Project Activity</h3>
                {projectAnalytics.recent_activities?.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {projectAnalytics.recent_activities.map((ev) => (
                      <div key={ev.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: 'var(--bg-main)', borderRadius: 6, fontSize: 13 }}>
                        <div>
                          <div style={{ fontWeight: 500 }}>{formatActivityText(ev)}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{ev.event_type}</div>
                        </div>
                        <span style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                          {formatTime(ev.created_at)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: '16px 0' }}>
                    No activities recorded for this project yet.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Upload Modal */}
      <Modal
        isOpen={isUploadModalOpen}
        onClose={() => !isUploading && setIsUploadModalOpen(false)}
        title="Upload PDF Material"
        footer={
          <>
            <button
              type="button"
              onClick={() => setIsUploadModalOpen(false)}
              className="btn btn-secondary"
              disabled={isUploading}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="upload-material-form"
              className="btn btn-primary"
              disabled={isUploading || !selectedFile}
            >
              {isUploading ? (
                <>
                  <span className="spinner"></span> Uploading & Processing...
                </>
              ) : (
                'Upload PDF'
              )}
            </button>
          </>
        }
      >
        {uploadError && <div className="alert alert-danger">{uploadError}</div>}
        <form id="upload-material-form" onSubmit={handleUpload}>
          <div className="form-group">
            <label className="form-label">Select PDF Document</label>
            <input
              type="file"
              accept=".pdf,application/pdf"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="form-input"
              style={{ padding: '8px 12px' }}
              required
            />
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
              Supported format: PDF only. Page text and chunks will be indexed for the AI Tutor and Quiz generator.
            </p>
          </div>

          {selectedFile && (
            <div style={{
              background: '#f8fafc',
              padding: '12px 14px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: 13
            }}>
              <div>
                <span style={{ fontWeight: 600 }}>{selectedFile.name}</span>
              </div>
              <span style={{ color: 'var(--success)', fontWeight: 600 }}>Ready to upload</span>
            </div>
          )}
        </form>
      </Modal>

      {/* Replace Material Modal */}
      <Modal
        isOpen={replacingMaterial !== null}
        onClose={() => !isReplacing && setReplacingMaterial(null)}
        title={`Replace Material: ${replacingMaterial?.filename || ''}`}
        footer={
          <>
            <button
              type="button"
              onClick={() => setReplacingMaterial(null)}
              className="btn btn-secondary"
              disabled={isReplacing}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="replace-material-form"
              className="btn btn-primary"
              disabled={isReplacing || !replaceFile}
            >
              {isReplacing ? (
                <>
                  <span className="spinner"></span> Replacing & Re-indexing...
                </>
              ) : (
                'Replace PDF'
              )}
            </button>
          </>
        }
      >
        <div style={{ marginBottom: 16, fontSize: 13, color: 'var(--text-muted)' }}>
          Replacing this PDF will permanently delete the existing file and its document chunks, and index the new document in its place.
        </div>
        {replaceError && <div className="alert alert-danger">{replaceError}</div>}
        <form id="replace-material-form" onSubmit={handleReplaceMaterial}>
          <div className="form-group">
            <label className="form-label">Select Replacement PDF</label>
            <input
              type="file"
              accept=".pdf,application/pdf"
              ref={replaceFileInputRef}
              onChange={handleReplaceFileChange}
              className="form-input"
              style={{ padding: '8px 12px' }}
              required
            />
          </div>

          {replaceFile && (
            <div style={{
              background: '#f8fafc',
              padding: '12px 14px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: 13
            }}>
              <div>
                <span style={{ fontWeight: 600 }}>{replaceFile.name}</span>
              </div>
              <span style={{ color: 'var(--success)', fontWeight: 600 }}>Ready to replace</span>
            </div>
          )}
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deletingMaterial !== null}
        onClose={() => !isDeleting && setDeletingMaterial(null)}
        title="Confirm Material Deletion"
        footer={
          <>
            <button
              type="button"
              onClick={() => setDeletingMaterial(null)}
              className="btn btn-secondary"
              disabled={isDeleting}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleDeleteMaterial}
              className="btn btn-danger"
              disabled={isDeleting}
            >
              {isDeleting ? (
                <>
                  <span className="spinner"></span> Deleting...
                </>
              ) : (
                'Delete Material'
              )}
            </button>
          </>
        }
      >
        <p style={{ fontSize: 14, color: 'var(--text-main)', lineHeight: 1.5 }}>
          Are you sure you want to delete <strong>{deletingMaterial?.filename}</strong>?
        </p>
        <p style={{ fontSize: 13, color: 'var(--danger)', marginTop: 8 }}>
          ⚠️ This will permanently remove the physical file from disk and purge all document chunks and vector embeddings. The AI Tutor and Quiz generator will no longer have access to this document.
        </p>
      </Modal>
    </div>
  );
}
