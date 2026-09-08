import React, { useState } from 'react';
import AuthLanding from './components/AuthLanding';
import Dashboard from './components/Dashboard';
import CandidateDashboard from './components/CandidateDashboard';
import InterviewPortal from './components/InterviewPortal';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [userRole, setUserRole] = useState(localStorage.getItem('role') || null);
  const [userFullName, setUserFullName] = useState(localStorage.getItem('full_name') || null);
  const [userEmail, setUserEmail] = useState(localStorage.getItem('email') || null);
  const [portalJobId, setPortalJobId] = useState(null);
  const [portalResumeId, setPortalResumeId] = useState(null);
  const [view, setView] = useState('dashboard');

  const handleLaunchPortal = (jobId, resumeId) => {
    setPortalJobId(jobId);
    setPortalResumeId(resumeId);
    setView('portal');
  };

  const handleLoginSuccess = (data) => {
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('role', data.role);
    localStorage.setItem('full_name', data.full_name);
    localStorage.setItem('email', data.email);

    setToken(data.access_token);
    setUserRole(data.role);
    setUserFullName(data.full_name);
    setUserEmail(data.email);
    setView('dashboard');
  };

  const handleLogout = () => {
    localStorage.clear();
    setToken(null);
    setUserRole(null);
    setUserFullName(null);
    setUserEmail(null);
    setView('dashboard');
  };

  if (!token) {
    return <AuthLanding onLoginSuccess={handleLoginSuccess} />;
  }

  if (view === 'portal') {
    return (
      <InterviewPortal 
        token={token}
        jobId={portalJobId}
        resumeId={portalResumeId}
        userFullName={userFullName}
        onBack={() => setView('dashboard')} 
      />
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-deep-space)' }}>
      {userRole === 'candidate' ? (
        <CandidateDashboard 
          token={token}
          userFullName={userFullName}
          userEmail={userEmail}
          onLaunchPortal={handleLaunchPortal}
          onLogout={handleLogout}
        />
      ) : (
        <Dashboard 
          token={token}
          userRole={userRole}
          userFullName={userFullName}
          userEmail={userEmail}
          onLogout={handleLogout}
          onLaunchPortal={handleLaunchPortal}
        />
      )}
    </div>
  );
}

export default App;
