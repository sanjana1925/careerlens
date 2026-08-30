import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useAppState } from '../context/AppStateContext';

export default function Dashboard() {
  const { email } = useAuth();
  const { targetRole, setTargetRole, selectedResumeId } = useAppState();
  const [role, setRole] = useState(targetRole);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  async function load(role) {
    setLoading(true);
    setError('');
    try {
      let resumeId = selectedResumeId;
      if (!resumeId) {
        const resumes = await api.listResumes();
        resumeId = resumes[0]?.id;
      }
      const result = await api.dashboardSummary(role || null, resumeId || null);
      setSummary(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(targetRole);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleRoleSubmit(e) {
    e.preventDefault();
    setTargetRole(role);
    load(role);
  }

  return (
    <div>
      <header className="page-header reveal">
        <h1>Welcome back{email ? `, ${email.split('@')[0]}` : ''}</h1>
        <p className="muted">
          Your <span className="accent-cursive">career readiness</span> at a glance.
        </p>
      </header>

      <form className="card form-inline reveal" onSubmit={handleRoleSubmit}>
        <label className="grow">
          Target role
          <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="AI Engineer" />
        </label>
        <button className="btn btn-primary" type="submit">Update</button>
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {summary && (
        <>
          <section className="card readiness-hero reveal" style={{ animationDelay: '0.05s' }}>
            <div className="hero-blob blob-a" />
            <div className="hero-blob blob-b" />
            <div className="hero-blob blob-c" />
            <div className="gauge-large" style={{ '--pct': `${Math.min(100, Math.round(summary.career_readiness_score))}%` }}>
              <div className="gauge-large-inner">
                <span className="gauge-large-value">{Math.round(summary.career_readiness_score)}</span>
                <span className="gauge-large-label">Readiness</span>
              </div>
            </div>
            <div className="readiness-stats">
              <div className="stat-card" style={{ flex: 1, minWidth: 140 }}>
                <div className="stat-value">{summary.ats_resume_score != null ? Math.round(summary.ats_resume_score) : '—'}</div>
                <div className="stat-label">ATS resume score</div>
              </div>
              <div className="stat-card" style={{ flex: 1, minWidth: 140 }}>
                <div className="stat-value">{Math.round(summary.profile_strength)}%</div>
                <div className="stat-label">Profile strength</div>
              </div>
            </div>
          </section>

          <div className="stat-grid reveal" style={{ animationDelay: '0.1s' }}>
            <div className="stat-card">
              <div className="stat-value">{summary.total_jobs_found}</div>
              <div className="stat-label">Total jobs found</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{summary.jobs_matching_profile}</div>
              <div className="stat-label">Jobs matching profile</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{summary.saved_job_count}</div>
              <div className="stat-label">Saved jobs</div>
            </div>
          </div>

          <div className="two-col reveal" style={{ alignItems: 'start', animationDelay: '0.15s' }}>
            <section className="card">
              <h2>Top recommended jobs</h2>
              {summary.top_recommended_jobs.length > 0 ? (
                <div className="rec-job-list">
                  {summary.top_recommended_jobs.map((j) => (
                    <a key={j.job_id} href={j.url} target="_blank" rel="noreferrer" className="rec-job-row">
                      <div>
                        <div className="rec-job-title">{j.title}</div>
                        <div className="muted" style={{ fontSize: '0.8rem' }}>{j.company || 'Unknown company'}</div>
                      </div>
                      <span className="badge">{Math.round(j.match_score)}%</span>
                    </a>
                  ))}
                </div>
              ) : (
                <p className="muted">
                  No matches yet — <Link to="/match" className="link">run job matching</Link> to see recommendations here.
                </p>
              )}
            </section>

            <section className="card">
              <h2>Skill gaps</h2>
              <p className="muted">
                See in-demand skills for your target role and where your resume falls short.
              </p>
              <Link to="/market" className="btn btn-primary">Open Market Intelligence</Link>
            </section>
          </div>

          {summary.recommended_actions.length > 0 && (
            <section className="card reveal" style={{ animationDelay: '0.2s' }}>
              <h2>Recommended actions</h2>
              <div className="action-list">
                {summary.recommended_actions.map((a) => (
                  <div key={a} className="action-item">
                    <span className="dot" />
                    {a}
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {loading && !summary && <p className="muted">Loading your dashboard…</p>}

      <div className="card-grid">
        <Link to="/jobs" className="action-card">
          <h3>1. Discover jobs</h3>
          <p>Search LinkedIn, Indeed, Glassdoor & Google in one pass via JobSpy.</p>
        </Link>
        <Link to="/resumes" className="action-card">
          <h3>2. Analyze your resume</h3>
          <p>Upload a resume, get an ATS score, strengths/weaknesses, and project repetition findings.</p>
        </Link>
        <Link to="/match" className="action-card">
          <h3>3. Match & rank jobs</h3>
          <p>Explainable match scores against collected jobs — matched vs. missing skills.</p>
        </Link>
        <Link to="/market" className="action-card">
          <h3>4. Market intelligence</h3>
          <p>See the most in-demand skills for your target role and where your profile has gaps.</p>
        </Link>
      </div>

      {summary && summary.recent_searches.length > 0 && (
        <section className="section">
          <h2>Recent activity</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Target role</th>
                <th>Sources</th>
                <th>Location</th>
                <th>Results</th>
              </tr>
            </thead>
            <tbody>
              {summary.recent_searches.map((s) => (
                <tr key={s.id}>
                  <td>{s.target_role}</td>
                  <td>{s.source_platforms}</td>
                  <td>{s.location || '—'}</td>
                  <td>{s.results_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
