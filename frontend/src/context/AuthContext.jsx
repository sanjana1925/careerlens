import { createContext, useContext, useEffect, useState } from 'react';
import { api, setAuthToken } from '../api/client';

const AuthContext = createContext(null);

const DEMO_EMAIL = 'demo@careerlens.app';
const DEMO_PASSWORD = 'demo-password-123';
const DEMO_NAME = 'Demo User';

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [email, setEmail] = useState(() => localStorage.getItem('email'));
  const [loading, setLoading] = useState(!token);
  const [error, setError] = useState('');

  function applySession(accessToken, userEmail) {
    setAuthToken(accessToken);
    setToken(accessToken);
    setEmail(userEmail);
    localStorage.setItem('email', userEmail);
  }

  useEffect(() => {
    if (token) return;

    let cancelled = false;

    async function autoSignIn() {
      try {
        let data;
        try {
          data = await api.login(DEMO_EMAIL, DEMO_PASSWORD);
        } catch {
          // Account may not exist yet, or another concurrent attempt is
          // creating it right now — try to register, then log in either way.
          try {
            await api.register({ email: DEMO_EMAIL, password: DEMO_PASSWORD, full_name: DEMO_NAME });
          } catch {
            /* ignore — most likely already registered */
          }
          data = await api.login(DEMO_EMAIL, DEMO_PASSWORD);
        }
        if (!cancelled) {
          applySession(data.access_token, DEMO_EMAIL);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    autoSignIn();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <AuthContext.Provider value={{ token, email, loading, error, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
