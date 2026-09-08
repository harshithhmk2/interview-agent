import React, { useState } from 'react';

const AuthLanding = ({ onLoginSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('candidate'); // candidate, interviewer, admin
  const [errorMsg, setErrorMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const extractErrorMessage = (errData, fallback) => {
    if (!errData) return fallback;
    if (typeof errData.detail === 'string') return errData.detail;
    if (Array.isArray(errData.detail)) {
      return errData.detail.map((e) => e.msg || e.message || JSON.stringify(e)).join('; ');
    }
    if (errData.message && typeof errData.message === 'string') return errData.message;
    return fallback;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!isLogin && password.length < 8) {
      setErrorMsg('Password must be at least 8 characters long.');
      return;
    }

    setLoading(true);

    const baseUrl = import.meta.env.VITE_API_BASE_URL || '';

    try {
      if (isLogin) {
        // Authenticate with form parameters
        const details = new URLSearchParams();
        details.append('username', email);
        details.append('password', password);

        const response = await fetch(`${baseUrl}/api/v1/auth/token`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: details,
        });

        if (!response.ok) {
          const errData = await response.json();
          throw new Error(extractErrorMessage(errData, 'Incorrect email or password'));
        }

        const data = await response.json();
        onLoginSuccess(data);
      } else {
        // Signup request
        const response = await fetch(`${baseUrl}/api/v1/auth/signup`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: email,
            password: password,
            full_name: fullName,
            role: role,
          }),
        });

        if (!response.ok) {
          const errData = await response.json();
          throw new Error(extractErrorMessage(errData, 'Failed to register account'));
        }

        // Auto login on signup success
        setIsLogin(true);
        setPassword('');
        setErrorMsg('Registration successful! Please login with your credentials.');
      }
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      className="page-view" 
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: 'var(--bg-deep-space)',
        padding: '20px'
      }}
    >
      <div 
        className="card-glass" 
        style={{
          width: '100%',
          maxWidth: '440px',
          padding: '40px 30px',
          border: '1px solid var(--border-glass)'
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '35px' }}>
          <div 
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '12px',
              background: 'var(--gradient-primary)',
              margin: '0 auto 15px',
              boxShadow: '0 0 20px 2px var(--accent-purple-glow)'
            }} 
          />
          <h1 style={{ fontSize: '26px', color: '#fff', marginBottom: '8px' }}>
            {isLogin ? 'Welcome Back' : 'Get Started'}
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
            {isLogin 
              ? 'Sign in to access your screening room' 
              : 'Create an account to register for screenings'}
          </p>
        </div>

        {errorMsg && (
          <div 
            style={{
              background: errorMsg.includes('successful') ? 'var(--status-emerald-glow)' : 'var(--status-coral-glow)',
              color: errorMsg.includes('successful') ? 'var(--status-emerald)' : 'var(--status-coral)',
              padding: '12px',
              borderRadius: '8px',
              fontSize: '13px',
              lineHeight: '1.4',
              marginBottom: '20px',
              border: `1px solid ${errorMsg.includes('successful') ? 'rgba(0, 245, 212, 0.1)' : 'rgba(255, 51, 102, 0.1)'}`
            }}
          >
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {!isLogin && (
            <div>
              <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: '600' }}>
                Full Name
              </label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="John Doe"
                style={{
                  width: '100%',
                  padding: '12px 14px',
                  borderRadius: '8px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid var(--border-glass)',
                  color: '#fff',
                  outline: 'none',
                  fontSize: '14px',
                  transition: 'border-color 0.2s ease'
                }}
              />
            </div>
          )}

          <div>
            <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: '600' }}>
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="candidate@company.com"
              style={{
                width: '100%',
                padding: '12px 14px',
                borderRadius: '8px',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-glass)',
                color: '#fff',
                outline: 'none',
                fontSize: '14px',
                transition: 'border-color 0.2s ease'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: '600' }}>
              Password
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              style={{
                width: '100%',
                padding: '12px 14px',
                borderRadius: '8px',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-glass)',
                color: '#fff',
                outline: 'none',
                fontSize: '14px',
                transition: 'border-color 0.2s ease'
              }}
            />
          </div>

          {!isLogin && (
            <div>
              <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: '600' }}>
                Account Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                style={{
                  width: '100%',
                  padding: '12px 14px',
                  borderRadius: '8px',
                  background: '#0E0E1B',
                  border: '1px solid var(--border-glass)',
                  color: '#fff',
                  outline: 'none',
                  fontSize: '14px'
                }}
              >
                <option value="candidate">Candidate (Job Applicant)</option>
                <option value="interviewer">Interviewer (Internal TA)</option>
                <option value="admin">Admin / Talent Acquisition Lead</option>
              </select>
            </div>
          )}

          <button 
            type="submit" 
            className="btn-primary" 
            disabled={loading}
            style={{ 
              marginTop: '10px',
              padding: '12px 0',
              fontWeight: '600',
              fontSize: '14px'
            }}
          >
            {loading ? 'Processing...' : (isLogin ? 'Login' : 'Create Account')}
          </button>
        </form>

        <div style={{ marginTop: '25px', textAlign: 'center', fontSize: '13px' }}>
          <span style={{ color: 'var(--text-secondary)' }}>
            {isLogin ? "Don't have an account? " : "Already have an account? "}
          </span>
          <button 
            onClick={() => {
              setIsLogin(!isLogin);
              setErrorMsg('');
            }}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--accent-cyan)',
              cursor: 'pointer',
              fontWeight: '500',
              outline: 'none'
            }}
          >
            {isLogin ? 'Sign Up' : 'Log In'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuthLanding;
