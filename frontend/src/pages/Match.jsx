import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAppState } from '../context/AppStateContext';

export default function Match() {
  const { selectedResumeId } = useAppState();
  const [resumes, setResumes] = useState([]);
  const [resumeId, setResumeId] = useState(selectedResumeId);
  const [matches, setMatches] = useState([]);
  const [jobsById, setJobsById] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [savedIds, setSavedIds] = useState(new Set());

  useEffect(() => {
    api.listResumes().then(setResumes).catch(() => {});
    api.listJobs({ limit: 100 }).then((jobs) => {
      setJobsById(Object.fromEntries(jobs.map((j) => [j.id, j])));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedResumeId) setResumeId(selectedResumeId);
  }, [selectedResumeId]);

  async function handleMatch() {
    if (!resumeId) return;
    setLoading(true);
    setError('');
    try {
      const results = await api.matchJobs({ resume_id: Number(resumeId) });
      results.sort((a, b) => b.match_score - a.match_score);
      setMatches(results);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(matchId) {
    try {
      await api.saveMatch(matchId);
      setSavedIds((prev) => new Set(prev).add(matchId));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>Explainable job matching</h1>
        <p className="muted">Rank collected jobs against your resume with matched/missing skills.</p>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="card form-inline">
        <select value={resumeId ?? ''} onChange={(e) => setResumeId(e.target.value)}>
          <option value="">Select a resume…</option>
          {resumes.map((r) => (
            <option key={r.id} value={r.id}>{r.filename}</option>
          ))}
        </select>
        <button className="btn btn-primary" onClick={handleMatch} disabled={!resumeId || loading}>
          {loading ? 'Matching…' : 'Match against collected jobs'}
        </button>
      </section>

      <section className="section">
        {matches.map((m) => {
          const job = jobsById[m.job_id];
          const matched = m.matched_skills.split(',').filter(Boolean);
          const missing = m.missing_skills.split(',').filter(Boolean);
          return (
            <div key={m.id} className="match-card">
              <div className="match-header">
                <div>
                  <h3>{job ? job.title : `Job #${m.job_id}`}</h3>
                  <p className="muted">{job ? `${job.company || 'Unknown company'} · ${job.location || 'Location unknown'}` : ''}</p>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                  <div className="match-score" style={{ '--pct': `${Math.min(100, Math.round(m.match_score))}%` }}>
                    {Math.round(m.match_score)}%
                  </div>
                  {m.semantic_score != null && (
                    <span className="badge" title="Semantic similarity from the Chroma vector search — catches related skills the keyword match above may miss">
                      ≈ {Math.round(m.semantic_score)}% semantic
                    </span>
                  )}
                </div>
              </div>
              <div className="mono-block">
                {matched.length ? (
                  matched.map((s) => <div key={s} className="good">✓ {s.trim()}</div>)
                ) : (
                  <div className="muted">No matched skills detected.</div>
                )}
                {missing.length > 0 && (
                  <>
                    <div>&nbsp;</div>
                    <div className="bad">⚠ Missing:</div>
                    {missing.map((s) => (
                      <div key={s} className="bad">&nbsp;&nbsp;{s.trim()}</div>
                    ))}
                  </>
                )}
              </div>
              <div className="match-actions">
                {job && <a className="link" href={job.url} target="_blank" rel="noreferrer">View posting</a>}
                <button
                  className="btn btn-ghost"
                  disabled={m.is_saved || savedIds.has(m.id)}
                  onClick={() => handleSave(m.id)}
                >
                  {m.is_saved || savedIds.has(m.id) ? 'Saved' : 'Save job'}
                </button>
              </div>
            </div>
          );
        })}
        {matches.length === 0 && !loading && <p className="muted">No matches yet — select a resume and run matching.</p>}
      </section>
    </div>
  );
}
