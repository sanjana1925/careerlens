import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAppState } from '../context/AppStateContext';
import { padLabel } from '../utils/format';

function emptyProject() {
  return { title: '', description: '' };
}

export default function Resumes() {
  const { selectedResumeId, setSelectedResumeId } = useAppState();
  const [resumes, setResumes] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [jobId, setJobId] = useState('');
  const [uploading, setUploading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [projects, setProjects] = useState([emptyProject()]);
  const [projectResult, setProjectResult] = useState(null);
  const [analyzingProjects, setAnalyzingProjects] = useState(false);
  const [autoDetecting, setAutoDetecting] = useState(false);
  const [error, setError] = useState('');

  function refreshResumes() {
    api.listResumes().then(setResumes).catch((err) => setError(err.message));
  }

  useEffect(() => {
    refreshResumes();
    api.listJobs({ limit: 100 }).then(setJobs).catch(() => {});
  }, []);

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const resume = await api.uploadResume(file);
      refreshResumes();
      setSelectedResumeId(resume.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  }

  async function handleAnalyze() {
    if (!selectedResumeId) return;
    setAnalyzing(true);
    setError('');
    setAnalysis(null);
    try {
      const result = await api.analyzeResume({
        resume_id: selectedResumeId,
        job_id: jobId ? Number(jobId) : null,
      });
      setAnalysis(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  }

  function updateProject(index, field, value) {
    setProjects((prev) => prev.map((p, i) => (i === index ? { ...p, [field]: value } : p)));
  }

  function addProject() {
    setProjects((prev) => [...prev, emptyProject()]);
  }

  function removeProject(index) {
    setProjects((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleAnalyzeProjects() {
    if (!selectedResumeId) return;
    const valid = projects.filter((p) => p.title.trim() && p.description.trim());
    if (valid.length === 0) return;
    setAnalyzingProjects(true);
    setError('');
    setProjectResult(null);
    try {
      const result = await api.analyzeProjects({ resume_id: selectedResumeId, projects: valid });
      setProjectResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzingProjects(false);
    }
  }

  async function handleAutoDetectProjects() {
    if (!selectedResumeId) return;
    setAutoDetecting(true);
    setError('');
    setProjectResult(null);
    try {
      const result = await api.autoAnalyzeProjects({ resume_id: selectedResumeId });
      setProjectResult(result);
      setProjects(result.projects.map((p) => ({ title: p.title, description: p.description })));
    } catch (err) {
      setError(err.message);
    } finally {
      setAutoDetecting(false);
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>Resume intelligence</h1>
        <p className="muted">ATS scoring, strengths/weaknesses, and project repetition detection.</p>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="card">
        <h2>1. Upload & select resume</h2>
        <div className="form-inline">
          <label className="file-label">
            {uploading ? 'Uploading…' : 'Upload resume (PDF/DOCX/TXT)'}
            <input type="file" accept=".pdf,.docx,.txt" onChange={handleUpload} hidden />
          </label>
          <select value={selectedResumeId ?? ''} onChange={(e) => setSelectedResumeId(Number(e.target.value) || null)}>
            <option value="">Select a resume…</option>
            {resumes.map((r) => (
              <option key={r.id} value={r.id}>
                {r.filename} — {new Date(r.uploaded_at).toLocaleString()}
              </option>
            ))}
          </select>
        </div>
      </section>

      <section className="card">
        <h2>2. ATS compatibility & resume analysis</h2>
        <div className="form-inline">
          <select value={jobId} onChange={(e) => setJobId(e.target.value)}>
            <option value="">Score generally (no specific job)</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.title} @ {j.company || 'Unknown'}
              </option>
            ))}
          </select>
          <button className="btn btn-primary" onClick={handleAnalyze} disabled={!selectedResumeId || analyzing}>
            {analyzing ? 'Analyzing…' : 'Run analysis'}
          </button>
        </div>

        {analysis && (
          <div className="analysis-result">
            <div className="mono-block" style={{ marginBottom: 20 }}>
              <div>ATS Score: {Math.round(analysis.ats_score)}/100</div>
              <div>&nbsp;</div>
              <div>
                {padLabel('Matched Keywords:', 22)}
                <span className="good">{analysis.matched_keywords.split(',').filter(Boolean).length}</span>
              </div>
              <div>
                {padLabel('Missing Keywords:', 22)}
                <span className="bad">{analysis.missing_keywords.split(',').filter(Boolean).length}</span>
              </div>
              <div>{padLabel('Skill Match:', 22)}{Math.round(analysis.skill_match_pct)}%</div>
            </div>
            <div className="two-col">
              <div>
                <h4>Strengths</h4>
                <p>{analysis.strengths}</p>
              </div>
              <div>
                <h4>Weaknesses</h4>
                <p>{analysis.weaknesses}</p>
              </div>
            </div>
            <div style={{ marginTop: 16 }}>
              <h4>Missing strong points</h4>
              <p>{analysis.missing_strengths}</p>
            </div>
            <div className="two-col">
              <div>
                <h4>Matched keywords</h4>
                <div className="tag-list">
                  {analysis.matched_keywords.split(',').filter(Boolean).map((k) => (
                    <span key={k} className="tag tag-good">{k.trim()}</span>
                  ))}
                </div>
              </div>
              <div>
                <h4>Missing keywords</h4>
                <div className="tag-list">
                  {analysis.missing_keywords.split(',').filter(Boolean).map((k) => (
                    <span key={k} className="tag tag-bad">{k.trim()}</span>
                  ))}
                </div>
              </div>
            </div>
            <h4>Suggestions</h4>
            <p>{analysis.suggestions}</p>
          </div>
        )}
      </section>

      <section className="card">
        <h2>3. Project quality & repetition detector</h2>
        <p className="muted">
          Auto-detect projects straight from your uploaded resume, or paste title/description pairs
          manually, to check for repetition and weak diversity.
        </p>
        <div className="form-inline" style={{ marginBottom: 12 }}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleAutoDetectProjects}
            disabled={!selectedResumeId || autoDetecting}
          >
            {autoDetecting ? 'Detecting…' : 'Auto-detect from resume'}
          </button>
        </div>
        {projects.map((project, i) => (
          <div key={i} className="project-row">
            <input
              placeholder="Project title"
              value={project.title}
              onChange={(e) => updateProject(i, 'title', e.target.value)}
            />
            <textarea
              placeholder="Project description"
              value={project.description}
              onChange={(e) => updateProject(i, 'description', e.target.value)}
              rows={2}
            />
            {projects.length > 1 && (
              <button type="button" className="btn btn-ghost" onClick={() => removeProject(i)}>Remove</button>
            )}
          </div>
        ))}
        <div className="form-inline">
          <button type="button" className="btn btn-ghost" onClick={addProject}>+ Add project</button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleAnalyzeProjects}
            disabled={!selectedResumeId || analyzingProjects}
          >
            {analyzingProjects ? 'Analyzing…' : 'Analyze projects'}
          </button>
        </div>

        {projectResult && (
          <div className="analysis-result">
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Category</th>
                    <th>Repetitive?</th>
                  </tr>
                </thead>
                <tbody>
                  {projectResult.projects.map((p) => (
                    <tr key={p.id}>
                      <td>{p.title}</td>
                      <td>{p.category || '—'}</td>
                      <td>{p.is_repetitive ? <span className="tag tag-bad">Yes</span> : <span className="tag tag-good">No</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <h4>Suggestions</h4>
            <ul>
              {projectResult.suggestions.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}
