import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAppState } from '../context/AppStateContext';

// Must match app/services/job_scraper.py's SUPPORTED_SOURCES — the installed
// python-jobspy version doesn't support Naukri despite earlier project notes.
const ALL_SOURCES = ['linkedin', 'indeed', 'glassdoor', 'google', 'zip_recruiter'];

// Common target-role titles, the way LinkedIn/Indeed prime their own search
// box — offered as a datalist so the field stays free-text but still gets
// one-click suggestions instead of requiring the user to know the exact title.
const COMMON_ROLES = [
  'Software Engineer', 'Senior Software Engineer', 'Frontend Developer',
  'Backend Developer', 'Full Stack Developer', 'Mobile Developer',
  'iOS Developer', 'Android Developer', 'DevOps Engineer', 'Site Reliability Engineer',
  'Cloud Engineer', 'Platform Engineer', 'Data Engineer', 'Data Scientist',
  'Data Analyst', 'Machine Learning Engineer', 'AI Engineer', 'Deep Learning Engineer',
  'Research Scientist', 'Product Manager', 'Technical Product Manager',
  'Project Manager', 'Engineering Manager', 'QA Engineer', 'Test Automation Engineer',
  'Security Engineer', 'Cybersecurity Analyst', 'Systems Administrator',
  'Network Engineer', 'Database Administrator', 'Business Analyst',
  'UI/UX Designer', 'Product Designer', 'Solutions Architect', 'Technical Writer',
  'Sales Engineer', 'Customer Success Manager', 'Marketing Manager',
];

const JOB_TYPES = [
  { value: '', label: 'Any type' },
  { value: 'fulltime', label: 'Full-time' },
  { value: 'parttime', label: 'Part-time' },
  { value: 'contract', label: 'Contract' },
  { value: 'internship', label: 'Internship' },
];

const HOURS_OLD_OPTIONS = [
  { value: '', label: 'Any time' },
  { value: '24', label: 'Past 24 hours' },
  { value: '72', label: 'Past 3 days' },
  { value: '168', label: 'Past week' },
  { value: '720', label: 'Past month' },
];

const SORT_OPTIONS = [
  { value: 'collected_at', label: 'Recently collected' },
  { value: 'date_posted', label: 'Date posted' },
  { value: 'max_amount', label: 'Salary' },
  { value: 'title', label: 'Title' },
];

export default function JobSearch() {
  const { targetRole, setTargetRole } = useAppState();
  const [role, setRole] = useState(targetRole);
  const [location, setLocation] = useState('');
  const [sources, setSources] = useState(['linkedin', 'indeed', 'glassdoor', 'google']);
  const [resultsWanted, setResultsWanted] = useState(20);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [jobType, setJobType] = useState('');
  const [isRemote, setIsRemote] = useState(false);
  const [hoursOld, setHoursOld] = useState('');
  const [distance, setDistance] = useState('');
  const [easyApply, setEasyApply] = useState(false);

  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [failedSources, setFailedSources] = useState([]);

  // Results list filters/sort — applied against already-collected jobs via GET /jobs.
  const [filterQuery, setFilterQuery] = useState('');
  const [filterSource, setFilterSource] = useState('');
  const [filterRemoteOnly, setFilterRemoteOnly] = useState(false);
  const [sortBy, setSortBy] = useState('collected_at');
  const [sortOrder, setSortOrder] = useState('desc');

  function loadJobs() {
    api
      .listJobs({
        limit: 50,
        q: filterQuery || null,
        source: filterSource || null,
        is_remote: filterRemoteOnly ? true : null,
        sort_by: sortBy,
        sort_order: sortOrder,
      })
      .then(setJobs)
      .catch(() => {});
  }

  useEffect(() => {
    loadJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterQuery, filterSource, filterRemoteOnly, sortBy, sortOrder]);

  function toggleSource(source) {
    setSources((prev) => (prev.includes(source) ? prev.filter((s) => s !== source) : [...prev, source]));
  }

  async function handleSearch(e) {
    e.preventDefault();
    setError('');
    setFailedSources([]);
    setLoading(true);
    try {
      const { jobs: results, failedSources: failed } = await api.searchJobs({
        target_role: role,
        location: location || null,
        sources,
        results_wanted: Number(resultsWanted),
        job_type: jobType || null,
        is_remote: isRemote || null,
        hours_old: hoursOld ? Number(hoursOld) : null,
        distance: distance ? Number(distance) : null,
        easy_apply: easyApply || null,
      });
      setJobs(results);
      setFailedSources(failed);
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
        <h1>Multi-platform job discovery</h1>
        <p className="muted">Powered by JobSpy — collects, cleans, and deduplicates listings across sources.</p>
      </header>

      <form className="card" onSubmit={handleSearch}>
        <div className="form-inline">
          <label className="grow">
            Target role
            <input
              required
              list="common-roles"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="AI Engineer"
            />
            <datalist id="common-roles">
              {COMMON_ROLES.map((r) => (
                <option key={r} value={r} />
              ))}
            </datalist>
          </label>
          <label>
            Location
            <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Remote / City" />
          </label>
          <label>
            Results per source
            <input type="number" min={1} max={100} value={resultsWanted} onChange={(e) => setResultsWanted(e.target.value)} />
          </label>
          <div className="source-toggles">
            {ALL_SOURCES.map((source) => (
              <button
                type="button"
                key={source}
                className={sources.includes(source) ? 'chip chip-active' : 'chip'}
                onClick={() => toggleSource(source)}
              >
                {source}
              </button>
            ))}
          </div>
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? 'Searching…' : 'Search jobs'}
          </button>
        </div>

        <button
          type="button"
          className="btn btn-ghost"
          style={{ marginTop: 14 }}
          onClick={() => setShowAdvanced((v) => !v)}
        >
          {showAdvanced ? 'Hide advanced filters' : 'Advanced filters'}
        </button>

        {showAdvanced && (
          <div className="form-inline" style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
            <label>
              Job type
              <select value={jobType} onChange={(e) => setJobType(e.target.value)}>
                {JOB_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </label>
            <label>
              Posted within
              <select value={hoursOld} onChange={(e) => setHoursOld(e.target.value)}>
                {HOURS_OLD_OPTIONS.map((h) => (
                  <option key={h.value} value={h.value}>{h.label}</option>
                ))}
              </select>
            </label>
            <label>
              Distance (miles)
              <input
                type="number"
                min={0}
                value={distance}
                disabled={isRemote}
                onChange={(e) => setDistance(e.target.value)}
                placeholder="50"
              />
            </label>
            <label style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <input type="checkbox" checked={isRemote} onChange={(e) => setIsRemote(e.target.checked)} style={{ width: 'auto' }} />
              Remote only
            </label>
            <label style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <input type="checkbox" checked={easyApply} onChange={(e) => setEasyApply(e.target.checked)} style={{ width: 'auto' }} />
              Easy apply only
            </label>
          </div>
        )}
      </form>

      {error && <div className="alert alert-error">{error}</div>}
      {!error && failedSources.length > 0 && (
        <div className="alert alert-warning">
          Couldn't reach: {failedSources.join(', ')}. Showing results from the other sources.
        </div>
      )}

      <section className="section">
        <div className="form-inline card" style={{ marginBottom: 0 }}>
          <label className="grow">
            Filter results
            <input value={filterQuery} onChange={(e) => setFilterQuery(e.target.value)} placeholder="Title or company" />
          </label>
          <label>
            Source
            <select value={filterSource} onChange={(e) => setFilterSource(e.target.value)}>
              <option value="">All sources</option>
              {ALL_SOURCES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>
          <label>
            Sort by
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              {SORT_OPTIONS.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="chip"
            onClick={() => setSortOrder((o) => (o === 'desc' ? 'asc' : 'desc'))}
          >
            {sortOrder === 'desc' ? '↓ Descending' : '↑ Ascending'}
          </button>
          <button
            type="button"
            className={filterRemoteOnly ? 'chip chip-active' : 'chip'}
            onClick={() => setFilterRemoteOnly((v) => !v)}
          >
            Remote only
          </button>
        </div>

        <h2 style={{ marginTop: 20 }}>{jobs.length} jobs</h2>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Company</th>
                <th>Location</th>
                <th>Type</th>
                <th>Source</th>
                <th>Salary</th>
                <th>Posted</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td>{job.title}</td>
                  <td>{job.company || '—'}</td>
                  <td>{job.location || '—'}{job.is_remote ? ' · Remote' : ''}</td>
                  <td>{job.job_type ? <span className="badge">{job.job_type}</span> : '—'}</td>
                  <td><span className="badge">{job.source}</span></td>
                  <td>
                    {job.min_amount || job.max_amount
                      ? `$${job.min_amount ?? '?'} – $${job.max_amount ?? '?'}`
                      : '—'}
                  </td>
                  <td>{job.date_posted ? new Date(job.date_posted).toLocaleDateString() : '—'}</td>
                  <td>
                    <a className="link" href={job.url} target="_blank" rel="noreferrer">View</a>
                  </td>
                </tr>
              ))}
              {jobs.length === 0 && (
                <tr>
                  <td colSpan={8} className="muted">No jobs yet — run a search above.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
