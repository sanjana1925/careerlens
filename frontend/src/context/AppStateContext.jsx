import { createContext, useContext, useState } from 'react';

const AppStateContext = createContext(null);

export function AppStateProvider({ children }) {
  const [targetRole, setTargetRole] = useState(() => localStorage.getItem('targetRole') || '');
  const [selectedResumeId, setSelectedResumeId] = useState(() => {
    const stored = localStorage.getItem('selectedResumeId');
    return stored ? Number(stored) : null;
  });

  function updateTargetRole(value) {
    setTargetRole(value);
    localStorage.setItem('targetRole', value);
  }

  function updateSelectedResumeId(value) {
    setSelectedResumeId(value);
    if (value) localStorage.setItem('selectedResumeId', String(value));
    else localStorage.removeItem('selectedResumeId');
  }

  return (
    <AppStateContext.Provider
      value={{ targetRole, setTargetRole: updateTargetRole, selectedResumeId, setSelectedResumeId: updateSelectedResumeId }}
    >
      {children}
    </AppStateContext.Provider>
  );
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used within AppStateProvider');
  return ctx;
}
