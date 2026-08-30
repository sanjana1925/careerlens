import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAppState } from '../context/AppStateContext';
import { asciiBar, padLabel } from '../utils/format';

export default function MarketIntelligence() {
  const { targetRole, setTargetRole, selectedResumeId } = useAppState();
  const [role, setRole] = useState(targetRole);
  const [resumes, setResumes] = useState([]);
  const [resumeId, setResumeId] = useState(selectedResumeId);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.listResumes().then(setResumes).catch(() => {});
  }, []);

  async function handleAnalyze(e) {
    e.preventDefault();
    if (!role) return;
    setLoading(true);
    setError('');
    try {
      const result = await api.marketIntelligence(role, resumeId || null);
      setData(result);
      setTargetRole(role);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>Job market & skill intelligence</h1>
        <p className="muted">Aggregated skill demand across collected postings for a target role.</p>
      </header>

      <form className="card form-inline" onSubmit={handleAnalyze}>
        <label className="grow">
          Target role
          <input required value={role} onChange={(e) => setRole(e.target.value)} placeholder="AI Engineer" />
        </label>
        <select value={resumeId ?? ''} onChange={(e) => setResumeId(e.target.value)}>
          <option value="">No resume (skip gap analysis)</option>
          {resumes.map((r) => (
            <option key={r.id} value={r.id}>{r.filename}</option>
          ))}
        </select>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? 'Analyzing…' : 'Analyze market'}
        </button>
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {data && (
        <>
          <p className="muted">Analyzed {data.jobs_analyzed} job postings for "{data.target_role}".</p>

          <section className="card">
            <h2>Most demanded skills</h2>
            {data.top_skills.length > 0 ? (
              <div className="mono-block">
                {data.top_skills.map((s) => (
                  <div key={s.skill}>
                    {padLabel(s.skill, 20)}
                    <span className="bar-fill">{asciiBar(s.percentage, 10)}</span>{' '}
                    {String(Math.round(s.percentage)).padStart(3, ' ')}%{'  '}
                    <span className="muted">({s.job_count} job{s.job_count === 1 ? '' : 's'})</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted">No skill data — collect more jobs for this role first.</p>
            )}
          </section>

          {data.skill_gaps.length > 0 && (
            <section className="card">
              <h2>Your skill gaps</h2>
              <div className="tag-list">
                {data.skill_gaps.map((g) => (
                  <span key={g} className="tag tag-bad">⚠ {g}</span>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
