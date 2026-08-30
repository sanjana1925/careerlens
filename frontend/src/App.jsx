import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppStateProvider } from './context/AppStateContext';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import JobSearch from './pages/JobSearch';
import Resumes from './pages/Resumes';
import Match from './pages/Match';
import MarketIntelligence from './pages/MarketIntelligence';

function AppRoutes() {
  const { loading, error } = useAuth();

  if (loading) {
    return (
      <div className="splash">
        <div className="brand center">
          <span className="brand-mark">CL</span>
          <span className="brand-name">CareerLens AI</span>
        </div>
        <p className="muted">Loading…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="splash">
        <div className="alert alert-error">Could not connect to the API: {error}</div>
      </div>
    );
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/jobs" element={<JobSearch />} />
        <Route path="/resumes" element={<Resumes />} />
        <Route path="/match" element={<Match />} />
        <Route path="/market" element={<MarketIntelligence />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppStateProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AppStateProvider>
      <div className="grain-overlay" aria-hidden="true" />
    </AuthProvider>
  );
}
