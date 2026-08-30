const BASE_URL = '/api';

// Held in a module variable (not just localStorage) so a request fired the
// instant a token is issued always sees it — reading localStorage directly
// here would race against the React effect that persists it.
let authToken = localStorage.getItem('token');

export function setAuthToken(token) {
  authToken = token;
  if (token) localStorage.setItem('token', token);
  else localStorage.removeItem('token');
}

function getToken() {
  return authToken;
}

async function request(path, { method = 'GET', body, form, auth = true, returnMeta = false } = {}) {
  const headers = {};
  if (body) headers['Content-Type'] = 'application/json';
  let sentToken = false;
  if (auth) {
    const token = getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
      sentToken = true;
    }
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: form ?? (body ? JSON.stringify(body) : undefined),
  });

  if (res.status === 401 && sentToken) {
    // The stored token is stale (expired, or from a backend that's since
    // restarted with different data) — AuthContext only auto-signs-in when
    // there's no token at all, so a stale one sits there causing silent 401s
    // on every request until storage is cleared by hand. Clear it and reload
    // so that auto-sign-in effect runs fresh instead.
    setAuthToken(null);
    localStorage.removeItem('email');
    window.location.reload();
    return new Promise(() => {}); // reload is about to unmount everything
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail ?? JSON.stringify(data);
    } catch {
      /* no JSON body */
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }

  if (res.status === 204) return returnMeta ? { data: null, headers: res.headers } : null;
  const data = await res.json();
  return returnMeta ? { data, headers: res.headers } : data;
}

export const api = {
  register: (payload) => request('/auth/register', { method: 'POST', body: payload, auth: false }),

  login: (email, password) => {
    const form = new URLSearchParams();
    form.set('username', email);
    form.set('password', password);
    return fetch(`${BASE_URL}/auth/login`, { method: 'POST', body: form }).then(async (res) => {
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Login failed');
      }
      return res.json();
    });
  },

  searchJobs: async (payload) => {
    const { data, headers } = await request('/jobs/search', { method: 'POST', body: payload, returnMeta: true });
    const failedSourcesHeader = headers.get('X-Failed-Sources');
    return { jobs: data, failedSources: failedSourcesHeader ? failedSourcesHeader.split(', ') : [] };
  },
  listJobs: (params = {}) => {
    const qs = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== null && value !== undefined && value !== '') qs.set(key, value);
    }
    return request(`/jobs?${qs.toString()}`);
  },

  uploadResume: (file) => {
    const form = new FormData();
    form.append('file', file);
    return request('/resumes/upload', { method: 'POST', form });
  },
  listResumes: () => request('/resumes'),
  analyzeResume: (payload) => request('/resumes/analyze', { method: 'POST', body: payload }),
  listAnalyses: (resumeId) => request(`/resumes/${resumeId}/analyses`),
  analyzeProjects: (payload) => request('/resumes/projects/analyze', { method: 'POST', body: payload }),
  autoAnalyzeProjects: (payload) => request('/resumes/projects/auto-analyze', { method: 'POST', body: payload }),

  matchJobs: (payload) => request('/match', { method: 'POST', body: payload }),
  saveMatch: (matchId) => request(`/match/${matchId}/save`, { method: 'POST' }),
  listSavedMatches: () => request('/match/saved'),
  marketIntelligence: (targetRole, resumeId) => {
    const params = new URLSearchParams({ target_role: targetRole });
    if (resumeId) params.set('resume_id', resumeId);
    return request(`/match/market-intelligence?${params.toString()}`);
  },

  dashboardSummary: (targetRole, resumeId) => {
    const params = new URLSearchParams();
    if (targetRole) params.set('target_role', targetRole);
    if (resumeId) params.set('resume_id', resumeId);
    const qs = params.toString();
    return request(`/dashboard/summary${qs ? `?${qs}` : ''}`);
  },
};
