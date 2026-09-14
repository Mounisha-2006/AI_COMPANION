const API_BASE = '';

function getToken() {
  return localStorage.getItem('token');
}

async function request(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Handle JSON vs FormData
  if (!(options.body instanceof FormData) && !headers['Content-Type'] && options.method && options.method !== 'GET') {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
      window.location.href = '/login';
    }
  }

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let errorMsg = data?.detail;
    if (!errorMsg) {
      if (response.status === 500 || response.status === 502 || response.status === 503 || response.status === 504) {
        errorMsg = 'Unable to connect to the backend API. Please ensure the backend server is running on http://localhost:8000.';
      } else {
        errorMsg = response.statusText || 'An error occurred';
      }
    }
    const error = new Error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
    error.status = response.status;
    error.data = data;
    throw error;
  }


  return data;
}

export const api = {
  auth: {
    login: (email, password) =>
      request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    register: (name, email, password) =>
      request('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ name, email, password }),
      }),
    me: () => request('/auth/me'),
  },
  spaces: {
    list: () => request('/spaces'),
    get: (id) => request(`/spaces/${id}`),
    create: (data) =>
      request('/spaces', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id, data) =>
      request(`/spaces/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: (id) =>
      request(`/spaces/${id}`, {
        method: 'DELETE',
      }),
  },
  projects: {
    list: (spaceId) => request(`/spaces/${spaceId}/projects`),
    get: (id) => request(`/projects/${id}`),
    create: (spaceId, data) =>
      request(`/spaces/${spaceId}/projects`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id, data) =>
      request(`/projects/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: (id) =>
      request(`/projects/${id}`, {
        method: 'DELETE',
      }),
  },
  materials: {
    list: (projectId) => request(`/projects/${projectId}/materials`),
    get: (id) => request(`/materials/${id}`),
    upload: (projectId, file) => {
      const formData = new FormData();
      formData.append('file', file);
      return request(`/projects/${projectId}/materials`, {
        method: 'POST',
        body: formData,
      });
    },
    delete: (projectId, materialId) =>
      request(`/projects/${projectId}/materials/${materialId}`, {
        method: 'DELETE',
      }),
    replace: (projectId, materialId, file) => {
      const formData = new FormData();
      formData.append('file', file);
      return request(`/projects/${projectId}/materials/${materialId}/replace`, {
        method: 'PUT',
        body: formData,
      });
    },
  },
  activity: {
    list: (limit = 20, skip = 0, projectId = null, eventType = null) => {
      const params = new URLSearchParams();
      params.append('limit', limit);
      params.append('skip', skip);
      if (projectId) params.append('project_id', projectId);
      if (eventType) params.append('event_type', eventType);
      return request(`/activity?${params.toString()}`);
    },
  },
  tutor: {
    chat: (projectId, message) =>
      request(`/projects/${projectId}/tutor/chat`, {
        method: 'POST',
        body: JSON.stringify({ message }),
      }),
    history: (projectId) => request(`/projects/${projectId}/tutor/history`),
    clearHistory: (projectId) =>
      request(`/projects/${projectId}/tutor/history`, {
        method: 'DELETE',
      }),
  },
  quiz: {
    start: (projectId, totalQuestions = 5) =>
      request(`/projects/${projectId}/quiz/start`, {
        method: 'POST',
        body: JSON.stringify({ total_questions: totalQuestions }),
      }),
    answer: (projectId, quizId, questionId, answerText) =>
      request(`/projects/${projectId}/quiz/${quizId}/answer`, {
        method: 'POST',
        body: JSON.stringify({ question_id: questionId, answer_text: answerText }),
      }),
    get: (projectId, quizId) => request(`/projects/${projectId}/quiz/${quizId}`),
    list: (projectId) => request(`/projects/${projectId}/quiz`),
  },
  assessment: {
    start: (projectId, totalQuestions = 3) =>
      request(`/projects/${projectId}/assessments/start`, {
        method: 'POST',
        body: JSON.stringify({ total_questions: totalQuestions }),
      }),
    submit: (projectId, assessmentId, questionId, responseText) =>
      request(`/projects/${projectId}/assessments/${assessmentId}/submit`, {
        method: 'POST',
        body: JSON.stringify({ question_id: questionId, response_text: responseText }),
      }),
    get: (projectId, assessmentId) => request(`/projects/${projectId}/assessments/${assessmentId}`),
    list: (projectId) => request(`/projects/${projectId}/assessments`),
  },
  mastery: {
    get: (projectId) => request(`/projects/${projectId}/mastery`),
  },
  growth: {
    get: (projectId) => request(`/projects/${projectId}/growth`),
  },
  recommendations: {
    list: (projectId) => request(`/projects/${projectId}/recommendations`),
    refresh: (projectId) =>
      request(`/projects/${projectId}/recommendations/generate`, {
        method: 'POST',
      }),
    complete: (projectId, recommendationId) =>
      request(`/projects/${projectId}/recommendations/${recommendationId}/complete`, {
        method: 'POST',
      }),
  },
  analytics: {
    getProject: (projectId) => request(`/projects/${projectId}/analytics`),
    getGlobal: () => request('/analytics/global'),
    getActivityHistory: (limit = 20, skip = 0, projectId = null, eventType = null) => {
      const params = new URLSearchParams();
      params.append('limit', limit);
      params.append('skip', skip);
      if (projectId) params.append('project_id', projectId);
      if (eventType) params.append('event_type', eventType);
      return request(`/activity?${params.toString()}`);
    },
  },
  admin: {
    getOverview: () => request('/admin/dashboard/overview'),
    listUsers: (limit = 50, skip = 0, search = null) => {
      const params = new URLSearchParams();
      params.append('limit', limit);
      params.append('skip', skip);
      if (search) params.append('search', search);
      return request(`/admin/users?${params.toString()}`);
    },
    inspectUser: (userId) => request(`/admin/users/${userId}`),
    getAIUsage: (limit = 50) => request(`/admin/ai-usage?limit=${limit}`),
    getAIEvaluation: () => request('/admin/ai-evaluation'),
    runAIEvaluation: () =>
      request('/admin/ai-evaluation/run', {
        method: 'POST',
      }),
    getSystemHealth: () => request('/admin/system-health'),
  },
};

