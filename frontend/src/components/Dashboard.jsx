import React, { useState, useEffect } from 'react';

const Dashboard = ({ token, userRole, userFullName, userEmail, onLogout, onLaunchPortal }) => {
  // Navigation tabs
  const [activeSubTab, setActiveSubTab] = useState('reports'); // reports, resumes, jobs

  // Data states
  const [reports, setReports] = useState([]);
  const [resumes, setResumes] = useState([]);
  const [jobs, setJobs] = useState([]);

  // Pagination states for reports
  const [reportsPage, setReportsPage] = useState(1);
  const [totalReports, setTotalReports] = useState(0);
  const reportsLimit = 10;

  // Pagination states for resumes
  const [resumesPage, setResumesPage] = useState(1);
  const resumesLimit = 10;

  // Pagination states for jobs
  const [jobsPage, setJobsPage] = useState(1);
  const jobsLimit = 10;

  // Active details panels
  const [activeReport, setActiveReport] = useState(null);
  const [activeResume, setActiveResume] = useState(null);
  const [reportTab, setReportTab] = useState('highlights'); // highlights, radar, transcript

  // Modal / Form states
  const [showJdModal, setShowJdModal] = useState(false);
  const [jdMode, setJdMode] = useState('create'); // create, edit, upload
  const [editingJdId, setEditingJdId] = useState(null);
  const [jdTitle, setJdTitle] = useState('');
  const [jdCompany, setJdCompany] = useState('Implere Technologies');
  const [jdStatus, setJdStatus] = useState('open');
  const [jdWorkMode, setJdWorkMode] = useState('onsite');
  const [jdLocation, setJdLocation] = useState('Bangalore');
  const [jdExperience, setJdExperience] = useState('3 - 5 Years');
  const [jdSalary, setJdSalary] = useState('₹ 15L - 18L / year');
  const [jdRawText, setJdRawText] = useState('');
  const [jdFile, setJdFile] = useState(null);
  const [jdMatchThreshold, setJdMatchThreshold] = useState(70);

  // Recruiter override fields
  const [overrideRec, setOverrideRec] = useState('hire');
  const [overrideNotes, setOverrideNotes] = useState('');

  // API base
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '';

  // Fetch Jobs list
  const fetchJobs = async (silent = false) => {
    if (!token) return;
    try {
      const response = await fetch(`${baseUrl}/api/v1/jobs`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.status === 401) {
        if (onLogout) onLogout();
        return;
      }
      if (response.ok) {
        const data = await response.json();
        setJobs(data);
      }
    } catch (err) {
      if (!silent) console.warn('Sync notice for jobs:', err.message);
    }
  };

  // Fetch Resumes / Candidate Applications list
  const fetchResumes = async (silent = false) => {
    if (!token) return;
    try {
      const response = await fetch(`${baseUrl}/api/v1/resumes`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.status === 401) {
        if (onLogout) onLogout();
        return;
      }
      if (response.ok) {
        const data = await response.json();
        setResumes(data);
      }
    } catch (err) {
      if (!silent) console.warn('Sync notice for resumes:', err.message);
    }
  };

  // Fetch Evaluation Reports with Pagination
  const fetchReports = async (silent = false) => {
    if (!token) return;
    try {
      const response = await fetch(`${baseUrl}/api/v1/reports?page=${reportsPage}&limit=${reportsLimit}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.status === 401) {
        if (onLogout) onLogout();
        return;
      }
      if (response.ok) {
        const data = await response.json();
        setReports(data.reports || []);
        setTotalReports(data.total_count || 0);
      }
    } catch (err) {
      if (!silent) console.warn('Sync notice for reports:', err.message);
    }
  };

  useEffect(() => {
    fetchJobs();
    fetchResumes();
    fetchReports();

    // Live auto-refresh jobs, candidate applications & evaluation reports every 5 seconds
    const interval = setInterval(() => {
      fetchJobs(true);
      fetchResumes(true);
      fetchReports(true);
    }, 5000);

    return () => clearInterval(interval);
  }, [token, reportsPage]);

  const [isSavingJd, setIsSavingJd] = useState(false);

  // Handle Job Description creation or update (Copy-Paste)
  const handleSaveJd = async (e) => {
    e.preventDefault();
    if (!jdTitle.trim()) {
      alert('Please enter a Position Title.');
      return;
    }
    if (!jdRawText.trim()) {
      alert('Please enter or paste the Job Description criteria text.');
      return;
    }

    setIsSavingJd(true);

    const payload = {
      title: jdTitle.trim(),
      company_name: jdCompany || 'Implere Technologies',
      status: jdStatus || 'open',
      work_mode: jdWorkMode || 'onsite',
      location: jdLocation || 'Bangalore',
      experience_range: jdExperience || '3 - 5 Years',
      salary_range: jdSalary || '₹ 15L - 18L / year',
      raw_text: jdRawText.trim(),
      match_threshold: jdMatchThreshold
    };

    try {
      let response;
      if (jdMode === 'edit' && editingJdId) {
        response = await fetch(`${baseUrl}/api/v1/jobs/${editingJdId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });
      } else {
        response = await fetch(`${baseUrl}/api/v1/jobs`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });
      }

      if (response.ok) {
        setShowJdModal(false);
        setJdTitle('');
        setJdRawText('');
        setEditingJdId(null);
        setIsSavingJd(false);
        fetchJobs();
      } else {
        const errData = await response.json();
        const msg = typeof errData.detail === 'string' ? errData.detail : (errData.message || 'Failed to save job description');
        alert(`Error saving job: ${msg}`);
        setIsSavingJd(false);
      }
    } catch (err) {
      console.error('Error saving JD:', err);
      alert(`Error saving job: ${err.message}`);
      setIsSavingJd(false);
    }
  };

  // Handle Job Description upload file
  const handleUploadJdFile = async (e) => {
    e.preventDefault();
    if (!jdTitle.trim()) {
      alert('Please enter a Position Title.');
      return;
    }
    if (!jdFile) {
      alert('Please select a PDF, Docx, or Txt document file to upload.');
      return;
    }

    setIsSavingJd(true);

    const formData = new FormData();
    formData.append('title', jdTitle.trim());
    formData.append('company_name', jdCompany || 'Implere Technologies');
    formData.append('status', jdStatus || 'open');
    formData.append('work_mode', jdWorkMode || 'onsite');
    formData.append('location', jdLocation || 'Bangalore');
    formData.append('experience_range', jdExperience || '3 - 5 Years');
    formData.append('salary_range', jdSalary || '₹ 15L - 18L / year');
    formData.append('file', jdFile);
    if (jdMatchThreshold) {
      formData.append('match_threshold', jdMatchThreshold);
    }

    try {
      const response = await fetch(`${baseUrl}/api/v1/jobs/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });

      if (response.ok) {
        setShowJdModal(false);
        setJdTitle('');
        setJdFile(null);
        setIsSavingJd(false);
        fetchJobs();
      } else {
        const errData = await response.json();
        const msg = typeof errData.detail === 'string' ? errData.detail : (errData.message || 'Failed to upload job description');
        alert(`Error uploading job: ${msg}`);
        setIsSavingJd(false);
      }
    } catch (err) {
      console.error('Error uploading JD:', err);
      alert(`Error uploading job: ${err.message}`);
      setIsSavingJd(false);
    }
  };

  // Handle Job Description deletion
  const handleDeleteJd = async (id) => {
    if (!window.confirm('Are you sure you want to delete this Job Description?')) return;
    try {
      const response = await fetch(`${baseUrl}/api/v1/jobs/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        fetchJobs();
      }
    } catch (err) {
      console.error('Error deleting JD:', err);
    }
  };

  // Handle proceed to next round manual override status
  const handleToggleProceedStatus = async (resumeId, currentStatus) => {
    try {
      const response = await fetch(`${baseUrl}/api/v1/resumes/${resumeId}/proceed`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ proceed_to_next_round: !currentStatus })
      });

      if (response.ok) {
        fetchResumes();
      }
    } catch (err) {
      console.error('Error updating proceed status:', err);
    }
  };

  // Handle report recruiter overrides
  const handleSaveReportOverride = async (e) => {
    e.preventDefault();
    if (!activeReport || !overrideNotes.trim()) return;

    try {
      const response = await fetch(`${baseUrl}/api/v1/reports/${activeReport.interview_id}/override`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          recruiter_override_recommendation: overrideRec,
          recruiter_notes: overrideNotes
        })
      });

      if (response.ok) {
        const updated = await response.json();
        setActiveReport(prev => ({
          ...prev,
          recruiter_override_recommendation: updated.recruiter_override_recommendation,
          recruiter_notes: updated.recruiter_notes,
          reviewed_at: updated.reviewed_at
        }));
        fetchReports();
        setOverrideNotes('');
        alert('Recruiter notes and recommendation overrides saved successfully!');
      }
    } catch (err) {
      console.error('Error saving override:', err);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 8.0 || score >= 80) return 'var(--status-emerald)';
    if (score >= 6.0 || score >= 60) return 'var(--status-amber)';
    return 'var(--status-coral)';
  };

  // Inject fallback mock data for testing context if offline or empty
  const displayJobs = jobs.length > 0 ? jobs : [
    {
      id: 'job-1',
      title: 'Senior Python Backend Developer',
      raw_text: 'Need someone who knows FastAPI and SQLAlchemy.',
      parsed_attributes: { tech_stack: ['FastAPI', 'SQLAlchemy'] }
    }
  ];

  const displayResumes = resumes.length > 0 ? resumes : [
    {
      id: 'res-1',
      candidate_name: 'Jane Doe',
      candidate_email: 'jane.doe@example.com',
      job_title: 'Sr. DevOps Engineer',
      match_score: 92,
      proceed_to_next_round: true
    }
  ];

  const displayReports = reports.length > 0 ? reports : [
    {
      id: 'rep-1',
      interview_id: 'int-1',
      candidate_name: 'Jane Doe',
      candidate_email: 'jane.doe@example.com',
      job_title: 'Sr. DevOps Engineer',
      overall_score: 9.2,
      recommendation: 'hire',
      primary_summary: '5+ years Kubernetes experience, AWS Certified, GitLab pipelines.',
      details: {
        Kubernetes: { score: 9.0, evidence: '5+ years experience' },
        GitLab: { score: 9.5, evidence: 'Built CI/CD pipelines' }
      }
    }
  ];

  const totalPages = Math.ceil((reports.length > 0 ? totalReports : displayReports.length) / reportsLimit) || 1;
  const paginatedReports = reports.length > 0
    ? reports
    : displayReports.slice((reportsPage - 1) * reportsLimit, reportsPage * reportsLimit);

  const totalResumesPages = Math.ceil(displayResumes.length / resumesLimit) || 1;
  const paginatedResumes = displayResumes.slice((resumesPage - 1) * resumesLimit, resumesPage * resumesLimit);

  const totalJobsPages = Math.ceil(displayJobs.length / jobsLimit) || 1;
  const paginatedJobs = displayJobs.slice((jobsPage - 1) * jobsLimit, jobsPage * jobsLimit);

  return (
    <div className="page-view" style={{ display: 'flex', minHeight: '100vh', position: 'relative' }}>
      
      {/* Sidebar Navigation */}
      <div 
        className="card-glass" 
        style={{
          width: '260px',
          borderRadius: '0 16px 16px 0',
          borderLeft: 'none',
          padding: '30px 20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          zIndex: 10
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '40px' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'var(--gradient-primary)' }} />
            <h2 style={{ fontSize: '18px', color: '#fff' }}>Interview Agent</h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div 
              className="mono" 
              onClick={() => setActiveSubTab('reports')}
              style={{ 
                color: activeSubTab === 'reports' ? 'var(--accent-cyan)' : 'var(--text-secondary)', 
                background: activeSubTab === 'reports' ? 'rgba(0, 210, 255, 0.05)' : 'transparent',
                padding: '10px', 
                borderRadius: '8px', 
                cursor: 'pointer' 
              }}
            >
              🎙️ Voice Reports
            </div>
            <div 
              className="mono" 
              onClick={() => setActiveSubTab('resumes')}
              style={{ 
                color: activeSubTab === 'resumes' ? 'var(--accent-cyan)' : 'var(--text-secondary)', 
                background: activeSubTab === 'resumes' ? 'rgba(0, 210, 255, 0.05)' : 'transparent',
                padding: '10px', 
                borderRadius: '8px', 
                cursor: 'pointer' 
              }}
            >
              📄 CV Applications
            </div>
            <div 
              className="mono" 
              onClick={() => setActiveSubTab('jobs')}
              style={{ 
                color: activeSubTab === 'jobs' ? 'var(--accent-cyan)' : 'var(--text-secondary)', 
                background: activeSubTab === 'jobs' ? 'rgba(0, 210, 255, 0.05)' : 'transparent',
                padding: '10px', 
                borderRadius: '8px', 
                cursor: 'pointer' 
              }}
            >
              📁 Job Descriptions
            </div>
            <div className="mono" style={{ color: 'var(--text-secondary)', padding: '10px', borderRadius: '8px', cursor: 'pointer' }} onClick={onLogout}>
              🚪 Log Out
            </div>
          </div>
        </div>

        <div>
          <div style={{ fontSize: '12px', color: '#fff', fontWeight: '500', marginBottom: '4px' }}>{userFullName}</div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'capitalize' }}>Role: {userRole}</div>
        </div>
      </div>

      {/* Main Workspace */}
      <div style={{ flex: 1, padding: '40px', overflowY: 'auto', maxWidth: (activeReport || activeResume) ? 'calc(100% - 460px)' : '100%', transition: 'max-width 0.3s ease' }}>
        
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
          <div>
            <h1 style={{ fontSize: '28px', color: '#fff', marginBottom: '8px' }}>Recruiter Dashboard</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              {activeSubTab === 'reports' && 'Voice Screening Reports — Review AI evaluation rubrics and turn-by-turn transcripts'}
              {activeSubTab === 'resumes' && 'Candidate Resume Applications — Parse resume skills matches and review proceed status'}
              {activeSubTab === 'jobs' && 'Job Postings — Create, edit, delete, or upload job description criteria'}
            </p>
          </div>
          {activeSubTab === 'jobs' && (
            <button 
              className="btn-primary" 
              onClick={() => {
                setJdMode('create');
                setEditingJdId(null);
                setJdTitle('');
                setJdCompany('Implere Technologies');
                setJdStatus('open');
                setJdWorkMode('onsite');
                setJdLocation('Bangalore');
                setJdExperience('3 - 5 Years');
                setJdSalary('₹ 15L - 18L / year');
                setJdRawText('');
                setJdFile(null);
                setJdMatchThreshold(70);
                setShowJdModal(true);
              }}
            >
              Add Job Description
            </button>
          )}
        </div>

        {/* KPIs */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px', marginBottom: '30px' }}>
          {[
            { label: 'Screened Candidates', val: displayResumes.length, color: 'var(--accent-cyan)' },
            { label: 'Active Positions', val: displayJobs.length, color: 'var(--accent-purple)' },
            { label: 'Avg Match Score', val: '87%', color: 'var(--status-emerald)' },
            { label: 'Pending Reviews', val: displayReports.length, color: 'var(--status-amber)' }
          ].map((k, idx) => (
            <div key={idx} className="card-glass" style={{ padding: '20px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px' }}>{k.label}</div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: k.color }}>{k.val}</div>
            </div>
          ))}
        </div>

        {/* Tab 1: Voice Reports (Grid View & Pagination) */}
        {activeSubTab === 'reports' && (
          <div className="page-view">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '40px' }} data-testid="reports-grid">
              {paginatedReports.map((report) => (
                <div 
                  key={report.id} 
                  className="card-glass" 
                  onClick={() => { setActiveReport(report); setActiveResume(null); }}
                  style={{ 
                    padding: '24px', 
                    cursor: 'pointer',
                    borderColor: activeReport?.id === report.id ? 'var(--accent-cyan)' : 'var(--border-glass)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '15px' }}>
                    <span 
                      style={{ 
                        padding: '4px 10px', 
                        borderRadius: '12px', 
                        fontSize: '11px', 
                        fontWeight: '600',
                        textTransform: 'uppercase',
                        background: report.recommendation === 'hire' ? 'var(--status-emerald-glow)' : 'var(--status-coral-glow)',
                        color: report.recommendation === 'hire' ? 'var(--status-emerald)' : 'var(--status-coral)'
                      }}
                    >
                      {report.recommendation.replace('_', ' ')}
                    </span>
                    <span style={{ fontSize: '20px', fontWeight: 'bold', color: getScoreColor(report.overall_score) }}>
                      {report.overall_score.toFixed(1)}
                    </span>
                  </div>
                  <h3 style={{ fontSize: '18px', color: '#fff', marginBottom: '6px' }}>{report.candidate_name}</h3>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '15px' }}>
                    Applied: {report.job_title}
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.5', display: '-webkit-box', WebkitLineClamp: '3', WebkitBoxOrient: 'vertical', overflow: 'hidden', marginBottom: '15px' }}>
                    {report.primary_summary}
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-glass)', paddingTop: '12px', marginTop: '12px' }}>
                    <button className="btn-secondary" style={{ padding: '6px 12px', fontSize: '11px' }}>
                      View Report
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '20px' }}>
                <button 
                  className="btn-secondary" 
                  disabled={reportsPage <= 1} 
                  onClick={() => setReportsPage(prev => Math.max(prev - 1, 1))}
                  style={{ opacity: reportsPage <= 1 ? 0.5 : 1 }}
                >
                  ◀ Prev
                </button>
                <span className="mono" style={{ color: '#fff' }}>
                  Page {reportsPage} of {totalPages}
                </span>
                <button 
                  className="btn-secondary" 
                  disabled={reportsPage >= totalPages} 
                  onClick={() => setReportsPage(prev => Math.min(prev + 1, totalPages))}
                  style={{ opacity: reportsPage >= totalPages ? 0.5 : 1 }}
                >
                  Next ▶
                </button>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Resume Applications (Proceed override) */}
        {activeSubTab === 'resumes' && (
          <div className="page-view">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px', marginBottom: '40px' }} data-testid="resumes-grid">
              {paginatedResumes.map((res) => (
                <div 
                  key={res.id} 
                  className="card-glass" 
                  style={{ padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                      <h3 style={{ fontSize: '18px', color: '#fff' }}>{res.candidate_name}</h3>
                      {res.match_score !== null && (
                        <span style={{ fontSize: '18px', fontWeight: 'bold', color: getScoreColor(res.match_score) }}>
                          {res.match_score.toFixed(0)}% Match
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>{res.candidate_email}</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
                      <strong>Role applied:</strong> {res.job_title || 'N/A'}
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-glass)', paddingTop: '15px' }}>
                    <div>
                      <span style={{ fontSize: '12px', color: 'var(--text-secondary)', marginRight: '10px' }}>Proceed status:</span>
                      <span 
                        style={{ 
                          fontSize: '11px', 
                          padding: '2px 8px', 
                          borderRadius: '10px', 
                          background: res.proceed_to_next_round ? 'var(--status-emerald-glow)' : 'var(--status-coral-glow)',
                          color: res.proceed_to_next_round ? 'var(--status-emerald)' : 'var(--status-coral)',
                          fontWeight: '600'
                        }}
                      >
                        {res.proceed_to_next_round ? 'PROCEED' : 'NO PROCEED'}
                      </span>
                    </div>
                    <button 
                      className="btn-secondary" 
                      onClick={() => handleToggleProceedStatus(res.id, res.proceed_to_next_round)}
                      style={{ padding: '6px 12px', fontSize: '12px' }}
                    >
                      {res.proceed_to_next_round ? 'Reject' : 'Approve'}
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination Controls */}
            {totalResumesPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '20px' }}>
                <button 
                  className="btn-secondary" 
                  disabled={resumesPage <= 1} 
                  onClick={() => setResumesPage(prev => Math.max(prev - 1, 1))}
                  style={{ opacity: resumesPage <= 1 ? 0.5 : 1 }}
                >
                  ◀ Prev
                </button>
                <span className="mono" style={{ color: '#fff' }}>
                  Page {resumesPage} of {totalResumesPages}
                </span>
                <button 
                  className="btn-secondary" 
                  disabled={resumesPage >= totalResumesPages} 
                  onClick={() => setResumesPage(prev => Math.min(prev + 1, totalResumesPages))}
                  style={{ opacity: resumesPage >= totalResumesPages ? 0.5 : 1 }}
                >
                  Next ▶
                </button>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Job Descriptions (Manage JDs) */}
        {activeSubTab === 'jobs' && (
          <div className="page-view">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px', marginBottom: '40px' }} data-testid="jobs-grid">
              {paginatedJobs.map((job) => (
                <div key={job.id} className="card-glass" style={{ padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div>
                    <h3 style={{ fontSize: '18px', color: '#fff', marginBottom: '8px' }}>{job.title}</h3>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '15px' }}>
                      {((job.parsed_attributes?.tech_stack && job.parsed_attributes.tech_stack.length > 0)
                        ? job.parsed_attributes.tech_stack
                        : ["Python", "Java", "C++", "C#", "Go", "Rust", "React", "Vue", "Angular", "Next.js", "Node.js", "Express", "FastAPI", "Flask", "Django", "Spring", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQL", "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "CI/CD", "Kafka", "GraphQL", "REST", "Microservices", "System Design", "OOPS", "PyTorch", "TensorFlow", "Machine Learning", "LLM", "LangChain", "LangGraph", "FAISS"].filter(t => new RegExp(`\\b${t.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')}\\b`, 'i').test((job.raw_text || '') + ' ' + (job.title || '')))
                      ).map((t, i) => (
                        <span key={i} style={{ background: 'rgba(0, 210, 255, 0.08)', border: '1px solid rgba(0, 210, 255, 0.2)', borderRadius: '4px', padding: '2px 6px', fontSize: '11px', color: '#fff' }}>
                          {t}
                        </span>
                      ))}
                    </div>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.5', display: '-webkit-box', WebkitLineClamp: '4', WebkitBoxOrient: 'vertical', overflow: 'hidden', marginBottom: '20px' }}>
                      {job.raw_text}
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', borderTop: '1px solid var(--border-glass)', paddingTop: '15px' }}>
                    <button 
                      className="btn-secondary" 
                      onClick={() => {
                        setJdMode('edit');
                        setEditingJdId(job.id);
                        setJdTitle(job.title);
                        setJdCompany(job.company_name || 'Implere Technologies');
                        setJdStatus(job.status || 'open');
                        setJdWorkMode(job.work_mode || 'onsite');
                        setJdLocation(job.location || 'Bangalore');
                        setJdExperience(job.experience_range || '3 - 5 Years');
                        setJdSalary(job.salary_range || '₹ 15L - 18L / year');
                        setJdRawText(job.raw_text);
                        setJdMatchThreshold(job.match_threshold || 70);
                        setShowJdModal(true);
                      }}
                      style={{ padding: '6px 12px', fontSize: '12px' }}
                    >
                      Edit
                    </button>
                    <button 
                      className="btn-secondary" 
                      onClick={() => handleDeleteJd(job.id)}
                      style={{ padding: '6px 12px', fontSize: '12px', borderColor: 'var(--status-coral)', color: 'var(--status-coral)' }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination Controls */}
            {totalJobsPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '20px' }}>
                <button 
                  className="btn-secondary" 
                  disabled={jobsPage <= 1} 
                  onClick={() => setJobsPage(prev => Math.max(prev - 1, 1))}
                  style={{ opacity: jobsPage <= 1 ? 0.5 : 1 }}
                >
                  ◀ Prev
                </button>
                <span className="mono" style={{ color: '#fff' }}>
                  Page {jobsPage} of {totalJobsPages}
                </span>
                <button 
                  className="btn-secondary" 
                  disabled={jobsPage >= totalJobsPages} 
                  onClick={() => setJobsPage(prev => Math.min(prev + 1, totalJobsPages))}
                  style={{ opacity: jobsPage >= totalJobsPages ? 0.5 : 1 }}
                >
                  Next ▶
                </button>
              </div>
            )}
          </div>
        )}

      </div>

      {/* Recruiter Evaluation Drawer (Slides-in from Right) */}
      {activeReport && (
        <div 
          className="card-glass page-view" 
          style={{
            position: 'fixed',
            right: 0,
            top: 0,
            bottom: 0,
            width: '420px',
            borderRadius: '16px 0 0 16px',
            borderRight: 'none',
            padding: '30px',
            boxShadow: '-10px 0 30px rgba(0, 0, 0, 0.5)',
            display: 'flex',
            flexDirection: 'column',
            zIndex: 100
          }}
          data-testid="report-drawer"
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '25px' }}>
            <h2 style={{ fontSize: '20px', color: '#fff' }}>Assessment Report</h2>
            <button style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', fontSize: '20px', cursor: 'pointer' }} onClick={() => setActiveReport(null)}>
              ✕
            </button>
          </div>

          {/* Profile Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '30px' }}>
            <div 
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                border: `3px solid ${getScoreColor(activeReport.overall_score)}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '20px',
                fontWeight: 'bold',
                color: '#fff'
              }}
            >
              {activeReport.overall_score.toFixed(1)}
            </div>
            <div>
              <h3 style={{ fontSize: '18px', color: '#fff' }}>{activeReport.candidate_name}</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>{activeReport.job_title}</p>
            </div>
          </div>

          {/* Tab Selector */}
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border-glass)', marginBottom: '20px' }}>
            {['highlights', 'radar', 'transcript'].map((tab) => (
              <button
                key={tab}
                onClick={() => setReportTab(tab)}
                style={{
                  flex: 1,
                  padding: '10px 0',
                  background: 'transparent',
                  border: 'none',
                  borderBottom: reportTab === tab ? '2px solid var(--accent-cyan)' : 'none',
                  color: reportTab === tab ? 'var(--text-primary)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '13px',
                  textTransform: 'capitalize',
                  outline: 'none'
                }}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div style={{ flex: 1, overflowY: 'auto', marginBottom: '20px' }}>
            {reportTab === 'highlights' && (
              <div className="page-view">
                <h4 style={{ fontSize: '14px', color: 'var(--status-emerald)', marginBottom: '10px' }}>Matched Strengths</h4>
                <ul style={{ paddingLeft: '18px', color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.6', marginBottom: '25px' }}>
                  {(activeReport.evidence?.highlights || ['5+ years Kubernetes experience', 'Certified AWS Solutions Architect', 'Built CI/CD pipelines in GitLab']).map((h, i) => (
                    <li key={i} style={{ marginBottom: '6px' }}>{h}</li>
                  ))}
                </ul>

                <h4 style={{ fontSize: '14px', color: 'var(--status-coral)', marginBottom: '10px' }}>Gaps Identified</h4>
                <ul style={{ paddingLeft: '18px', color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.6', marginBottom: '25px' }}>
                  {(activeReport.evidence?.gaps || ['Limited Terraform exposure', 'Minimal Python backend development']).map((g, i) => (
                    <li key={i} style={{ marginBottom: '6px' }}>{g}</li>
                  ))}
                </ul>
              </div>
            )}

            {reportTab === 'radar' && (
              <div className="page-view" data-testid="skills-radar">
                <h4 style={{ fontSize: '14px', color: '#fff', marginBottom: '15px', textAlign: 'center' }}>Topic Competency Breakdown</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {Object.entries(activeReport.details || {}).map(([topic, data], idx) => {
                    const score = typeof data === 'object' ? data.score : data;
                    const pct = Math.min(100, Math.max(0, (score / 10) * 100));
                    return (
                      <div key={idx} style={{ background: 'rgba(255,255,255,0.02)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#fff', marginBottom: '6px' }}>
                          <span style={{ fontWeight: '600' }}>{topic}</span>
                          <span style={{ color: getScoreColor(score), fontWeight: 'bold' }}>{score.toFixed(1)} / 10</span>
                        </div>
                        <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ width: `${pct}%`, height: '100%', background: getScoreColor(score), transition: 'width 0.3s ease' }} />
                        </div>
                      </div>
                    );
                  })}
                  {(!activeReport.details || Object.keys(activeReport.details).length === 0) && (
                    <p style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center' }}>No category breakdowns available.</p>
                  )}
                </div>
              </div>
            )}

            {reportTab === 'transcript' && (
              <div className="page-view" style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                {(activeReport.transcript || [
                  { speaker: 'AI', text: 'Welcome Jane. Can you describe your experience orchestrating microservices?', time: '0:00' },
                  { speaker: 'Candidate', text: 'Sure! I managed a cluster of 50+ microservices using Kubernetes on AWS EKS...', time: '0:15' }
                ]).map((t, i) => (
                  <div key={i} style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 'bold', color: t.speaker === 'AI' ? 'var(--accent-purple)' : 'var(--accent-cyan)' }}>{t.speaker}</span>
                      <span>{t.time}</span>
                    </div>
                    <p style={{ fontSize: '13px', color: '#fff', lineHeight: '1.5' }}>{t.text}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Override Form */}
          <div style={{ borderTop: '1px solid var(--border-glass)', paddingTop: '20px' }}>
            <h4 style={{ fontSize: '14px', color: '#fff', marginBottom: '10px' }}>Log Assessment Decision</h4>
            <form onSubmit={handleSaveReportOverride} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Recommendation:</span>
                <select 
                  value={overrideRec} 
                  onChange={(e) => setOverrideRec(e.target.value)}
                  style={{ background: '#0E0E1B', border: '1px solid var(--border-glass)', borderRadius: '6px', color: '#fff', padding: '4px 10px', fontSize: '12px' }}
                >
                  <option value="hire">Hire</option>
                  <option value="no_hire">No Hire</option>
                  <option value="follow_up">Follow Up</option>
                </select>
              </div>
              <textarea 
                required
                value={overrideNotes}
                onChange={(e) => setOverrideNotes(e.target.value)}
                placeholder="Log recruiter notes and hiring feedback here (minimum 10 chars)..."
                style={{ width: '100%', height: '80px', padding: '8px', border: '1px solid var(--border-glass)', borderRadius: '6px', background: 'rgba(255,255,255,0.03)', color: '#fff', fontSize: '12px', outline: 'none', resize: 'none' }}
              />
              <button type="submit" className="btn-primary" style={{ padding: '8px 0', fontSize: '13px' }}>
                Save Override notes
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Add / Edit / Upload Job Description Modal */}
      {showJdModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200 }}>
          <div className="card-glass" style={{ width: '500px', padding: '30px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '18px', color: '#fff' }}>
                {jdMode === 'create' && 'Add Job Description'}
                {jdMode === 'edit' && 'Edit Job Description'}
                {jdMode === 'upload' && 'Upload Job Description File'}
              </h3>
              <button type="button" style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', fontSize: '18px', cursor: 'pointer' }} onClick={() => setShowJdModal(false)}>✕</button>
            </div>

            {/* Mode selection tabs */}
            {jdMode !== 'edit' && (
              <div style={{ display: 'flex', borderBottom: '1px solid var(--border-glass)', marginBottom: '20px' }}>
                <button 
                  type="button"
                  onClick={() => setJdMode('create')}
                  style={{ flex: 1, padding: '8px 0', background: 'transparent', border: 'none', borderBottom: jdMode === 'create' ? '2px solid var(--accent-cyan)' : 'none', color: jdMode === 'create' ? '#fff' : 'var(--text-secondary)', cursor: 'pointer', fontSize: '13px' }}
                >
                  Copy-Paste text
                </button>
                <button 
                  type="button"
                  onClick={() => setJdMode('upload')}
                  style={{ flex: 1, padding: '8px 0', background: 'transparent', border: 'none', borderBottom: jdMode === 'upload' ? '2px solid var(--accent-cyan)' : 'none', color: jdMode === 'upload' ? '#fff' : 'var(--text-secondary)', cursor: 'pointer', fontSize: '13px' }}
                >
                  Upload document File
                </button>
              </div>
            )}

            <form onSubmit={jdMode === 'upload' ? handleUploadJdFile : handleSaveJd} style={{ display: 'flex', flexDirection: 'column', gap: '15px', maxHeight: '75vh', overflowY: 'auto', paddingRight: '5px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '6px' }}>Position Title</label>
                <input 
                  type="text" 
                  required
                  value={jdTitle}
                  onChange={(e) => setJdTitle(e.target.value)}
                  placeholder="e.g. Python Developer"
                  style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-glass)', borderRadius: '6px', color: '#fff', outline: 'none', fontSize: '13px' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '6px' }}>Company Name</label>
                  <input 
                    type="text" 
                    required
                    value={jdCompany}
                    onChange={(e) => setJdCompany(e.target.value)}
                    placeholder="e.g. Implere Technologies"
                    style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-glass)', borderRadius: '6px', color: '#fff', outline: 'none', fontSize: '13px' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '6px' }}>Status</label>
                  <select 
                    value={jdStatus}
                    onChange={(e) => setJdStatus(e.target.value)}
                    style={{ width: '100%', padding: '10px', background: 'rgba(20, 20, 30, 0.95)', border: '1px solid var(--border-glass)', borderRadius: '6px', color: '#fff', outline: 'none', fontSize: '13px' }}
                  >
                    <option value="open">Open</option>
                    <option value="closed">Closed</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '6px' }}>Work Mode</label>
                  <select 
                    value={jdWorkMode}
                    onChange={(e) => setJdWorkMode(e.target.value)}
                    style={{ width: '100%', padding: '10px', background: 'rgba(20, 20, 30, 0.95)', border: '1px solid var(--border-glass)', borderRadius: '6px', color: '#fff', outline: 'none', fontSize: '13px' }}
                  >
                    <option value="onsite">Onsite</option>
                    <option value="remote">Remote</option>
                    <option value="hybrid">Hybrid</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '6px' }}>Location</label>
                  <input 
                    type="text" 
                    value={jdLocation}
                    onChange={(e) => setJdLocation(e.target.value)}
                    placeholder="e.g. Bangalore"
                    style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-glass)', borderRadius: '6px', color: '#fff', outline: 'none', fontSize: '13px' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '6px' }}>Experience</label>
                  <input 
                    type="text" 
                    value={jdExperience}
                    onChange={(e) => setJdExperience(e.target.value)}
                    placeholder="e.g. 3 - 5 Years"
                    style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-glass)', borderRadius: '6px', color: '#fff', outline: 'none', fontSize: '13px' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '6px' }}>Salary Range</label>
                  <input 
                    type="text" 
                    value={jdSalary}
                    onChange={(e) => setJdSalary(e.target.value)}
                    placeholder="e.g. ₹ 15L - 18L / year"
                    style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-glass)', borderRadius: '6px', color: '#fff', outline: 'none', fontSize: '13px' }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '6px' }}>Minimum Match Threshold (%)</label>
                <input 
                  type="number" 
                  min="0"
                  max="100"
                  value={jdMatchThreshold}
                  onChange={(e) => setJdMatchThreshold(parseFloat(e.target.value) || 0)}
                  placeholder="e.g. 70"
                  style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-glass)', borderRadius: '6px', color: '#fff', outline: 'none', fontSize: '13px' }}
                />
              </div>

              {jdMode === 'upload' ? (
                <div>
                  <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '6px' }}>Document File (PDF/Docx/Txt)</label>
                  <input 
                    type="file" 
                    required
                    accept=".pdf,.docx,.txt"
                    onChange={(e) => setJdFile(e.target.files[0])}
                    style={{ color: '#fff', fontSize: '13px', padding: '10px 0' }}
                  />
                </div>
              ) : (
                <div>
                  <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '6px' }}>Job Description criteria</label>
                  <textarea 
                    required
                    value={jdRawText}
                    onChange={(e) => setJdRawText(e.target.value)}
                    placeholder="Paste job details, stack required, and experience criteria here..."
                    style={{ width: '100%', height: '180px', padding: '10px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-glass)', borderRadius: '6px', color: '#fff', outline: 'none', resize: 'none', fontSize: '13px' }}
                  />
                </div>
              )}

              <div style={{ display: 'flex', gap: '15px', justifyContent: 'flex-end', marginTop: '10px' }}>
                <button type="button" className="btn-secondary" onClick={() => setShowJdModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={isSavingJd} style={{ opacity: isSavingJd ? 0.7 : 1 }}>
                  {isSavingJd ? 'Parsing & Saving Job...' : (jdMode === 'edit' ? 'Update Job' : 'Save Job Posting')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};

export default Dashboard;
