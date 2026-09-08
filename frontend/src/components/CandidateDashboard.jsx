import React, { useState, useEffect } from 'react';

const CandidateDashboard = ({ token, userFullName, userEmail, onLaunchPortal, onLogout }) => {
  const [jobs, setJobs] = useState([]);
  const [appliedJobIds, setAppliedJobIds] = useState([]);
  const [appliedResumesMap, setAppliedResumesMap] = useState({});
  const [selectedJob, setSelectedJob] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');
  const [applicationSuccess, setApplicationSuccess] = useState(false);
  const [appliedJobTitle, setAppliedJobTitle] = useState('');
  const [createdResumeId, setCreatedResumeId] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const jobsPerPage = 10;

  const baseUrl = import.meta.env.VITE_API_BASE_URL || '';

  const indexOfLastJob = currentPage * jobsPerPage;
  const indexOfFirstJob = indexOfLastJob - jobsPerPage;
  const currentJobs = jobs.slice(indexOfFirstJob, indexOfLastJob);
  const totalPages = Math.ceil(jobs.length / jobsPerPage);

  const getDaysAgoText = (dateString) => {
    if (!dateString) return 'Posted 5 days ago';
    const posted = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - posted);
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return 'Posted today';
    if (diffDays === 1) return 'Posted 1 day ago';
    return `Posted ${diffDays} days ago`;
  };

  const [completedScreeningsMap, setCompletedScreeningsMap] = useState({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};
        const [jobsRes, appsRes] = await Promise.all([
          fetch(`${baseUrl}/api/v1/jobs`, { headers: authHeaders }),
          token ? fetch(`${baseUrl}/api/v1/resumes/my-applications`, { headers: authHeaders }) : Promise.resolve({ ok: false })
        ]);

        if (appsRes && appsRes.status === 401) {
          if (onLogout) onLogout();
          return;
        }
        if (jobsRes.ok) {
          const data = await jobsRes.json();
          setJobs(data);
        }
        if (appsRes && appsRes.ok) {
          const appliedData = await appsRes.json();
          const ids = [];
          const map = {};
          const completedMap = {};
          (appliedData || []).forEach(item => {
            const jId = typeof item === 'string' ? item : item.job_id;
            const rId = typeof item === 'object' ? item.resume_id : null;
            const isCompleted = typeof item === 'object' ? !!item.screening_completed : false;
            if (jId) {
              ids.push(jId);
              if (rId) map[jId] = rId;
              completedMap[jId] = isCompleted;
            }
          });
          setAppliedJobIds(ids);
          setAppliedResumesMap(map);
          setCompletedScreeningsMap(completedMap);
        }
      } catch (err) {
        console.error('Error fetching candidate dashboard data:', err);
      }
    };
    fetchData();
  }, [token]);

  const handleUploadResume = async (e) => {
    const file = e.target.files[0];
    if (!file || !selectedJob) return;

    if (appliedJobIds.includes(selectedJob.id)) {
      alert('You have already applied for this position.');
      return;
    }

    setIsUploading(true);
    setUploadProgress('Submitting application...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${baseUrl}/api/v1/resumes?job_id=${selectedJob.id}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) {
        const errData = await response.json();
        const msg = typeof errData.detail === 'string' 
          ? errData.detail 
          : (errData.message || 'Failed to submit application');
        throw new Error(msg);
      }

      const data = await response.json();
      setCreatedResumeId(data.id);
      setAppliedJobTitle(selectedJob.title);
      setAppliedJobIds((prev) => [...prev, selectedJob.id]);
      setApplicationSuccess(true);
      setIsUploading(false);
      setUploadProgress('');
    } catch (err) {
      alert(`Application status: ${err.message}`);
      setIsUploading(false);
      setUploadProgress('');
    }
  };

  const handleStartScreening = () => {
    if (selectedJob && createdResumeId) {
      onLaunchPortal(selectedJob.id, createdResumeId);
    }
  };

  if (applicationSuccess) {
    return (
      <div className="page-view" style={{ maxWidth: '650px', margin: '80px auto', padding: '20px' }}>
        <div className="card-glass" style={{ padding: '50px 40px', textAlign: 'center', border: '1px solid var(--border-glass)' }}>
          <div 
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              background: 'var(--status-emerald-glow)',
              color: 'var(--status-emerald)',
              fontSize: '28px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 25px',
              border: '2px solid var(--status-emerald)'
            }}
          >
            ✓
          </div>
          <h2 style={{ fontSize: '26px', color: '#fff', marginBottom: '15px' }}>Application Submitted!</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: '1.6', marginBottom: '35px' }}>
            Thank you for applying to the <strong>{appliedJobTitle}</strong> position. Your resume has been uploaded and securely processed by the AI engine. The Talent Acquisition team has been notified.
          </p>
          
          <div style={{ background: 'rgba(157, 78, 221, 0.05)', border: '1px solid rgba(157, 78, 221, 0.15)', borderRadius: '12px', padding: '20px', marginBottom: '30px', textAlign: 'left' }}>
            <h4 style={{ color: '#fff', fontSize: '15px', marginBottom: '8px' }}>🎙️ Take the Voice Screening Now</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.5' }}>
              We invite you to participate in an interactive automated voice screening. This will assess your alignment on key qualifications and forward evidence of your skill highlights directly to recruiters.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '15px', justifyContent: 'center' }}>
            <button className="btn-secondary" onClick={() => setApplicationSuccess(false)}>Back to Openings</button>
            <button className="btn-primary" onClick={handleStartScreening}>Start Voice Screening</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-view" style={{ display: 'flex', minHeight: '100vh' }}>
      
      {/* Candidate Sidebar */}
      <div 
        className="card-glass" 
        style={{
          width: '260px',
          borderRadius: '0 16px 16px 0',
          borderLeft: 'none',
          padding: '30px 20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between'
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '40px' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'var(--gradient-primary)' }} />
            <h2 style={{ fontSize: '18px', color: '#fff' }}>CareerPortal</h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div className="mono" style={{ color: 'var(--accent-cyan)', background: 'rgba(0, 210, 255, 0.05)', padding: '10px', borderRadius: '8px', cursor: 'pointer' }}>
              ✦ Open Roles
            </div>
            <div className="mono" style={{ color: 'var(--text-secondary)', padding: '10px', borderRadius: '8px', cursor: 'pointer' }} onClick={onLogout}>
              🚪 Log Out
            </div>
          </div>
        </div>

        <div>
          <div style={{ fontSize: '12px', color: '#fff', fontWeight: '500', marginBottom: '4px' }}>{userFullName}</div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{userEmail}</div>
        </div>
      </div>

      {/* Main Jobs Listing */}
      <div style={{ flex: 1, padding: '40px', overflowY: 'auto' }}>
        <div style={{ marginBottom: '40px' }}>
          <h1 style={{ fontSize: '28px', color: '#fff', marginBottom: '8px' }}>Open Positions</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Explore active job opportunities, review requirements, and submit your screening application.</p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: selectedJob ? '1fr 1.1fr' : '1fr', gap: '30px', transition: 'all 0.3s ease' }}>
          
          {/* Job Postings Column with Grid & Pagination */}
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: selectedJob ? '1fr' : '1fr 1fr', gap: '20px' }}>
              {currentJobs.map((job) => {
                const hasApplied = appliedJobIds.includes(job.id);
                const isOpen = (job.status || 'open').toLowerCase() === 'open';
                const company = job.company_name || 'Implere Technologies';
                const daysAgo = getDaysAgoText(job.created_at);
                const workMode = (job.work_mode || 'Onsite').toUpperCase();
                const experience = job.experience_range || `${job.parsed_attributes?.minimum_experience_years || '3 - 5'} Years`;
                const salary = job.salary_range || '₹ 15L - 18L / year';
                const location = job.location || 'Bangalore';
                const requiredSkills = (job.parsed_attributes?.tech_stack && job.parsed_attributes.tech_stack.length > 0) 
                  ? job.parsed_attributes.tech_stack 
                  : (job.raw_text 
                      ? ["Python", "Java", "C++", "C#", "Go", "Rust", "React", "Vue", "Angular", "Next.js", "Node.js", "Express", "FastAPI", "Flask", "Django", "Spring", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQL", "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "CI/CD", "Kafka", "GraphQL", "REST", "Microservices", "System Design", "OOPS", "PyTorch", "TensorFlow", "Machine Learning", "LLM", "LangChain", "LangGraph", "FAISS"].filter(t => new RegExp(`\\b${t.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')}\\b`, 'i').test(job.raw_text + ' ' + (job.title || ''))) 
                      : []
                    );
                const finalRequiredSkills = requiredSkills.length > 0 ? requiredSkills : ['Software Engineering'];
                const preferredSkills = job.parsed_attributes?.preferred_skills || [];

                return (
                  <div 
                    key={job.id} 
                    className="card-glass" 
                    onClick={() => { setSelectedJob(job); setApplicationSuccess(false); }}
                    style={{ 
                      padding: '24px', 
                      cursor: 'pointer',
                      borderColor: selectedJob?.id === job.id ? 'var(--accent-cyan)' : 'var(--border-glass)',
                      transform: selectedJob?.id === job.id ? 'scale(1.01)' : 'none',
                      position: 'relative'
                    }}
                  >
                    {/* Header Row: Role Title & Application Status Badge */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                      <div>
                        <h3 style={{ fontSize: '20px', color: '#fff', fontWeight: '700', marginBottom: '4px' }}>{job.title}</h3>
                        <div style={{ fontSize: '14px', color: 'var(--accent-cyan)', fontWeight: '600' }}>{company}</div>
                      </div>
                      <span 
                        style={{ 
                          padding: '4px 10px', 
                          borderRadius: '20px', 
                          fontSize: '11px', 
                          fontWeight: '700',
                          textTransform: 'uppercase',
                          background: completedScreeningsMap[job.id] ? 'rgba(0, 245, 212, 0.2)' : (hasApplied ? 'rgba(0, 245, 212, 0.12)' : (isOpen ? 'rgba(0, 210, 255, 0.12)' : 'rgba(255, 51, 102, 0.12)')),
                          color: (completedScreeningsMap[job.id] || hasApplied) ? 'var(--status-emerald)' : (isOpen ? 'var(--accent-cyan)' : 'var(--status-coral)'),
                          border: `1px solid ${(completedScreeningsMap[job.id] || hasApplied) ? 'var(--status-emerald)' : (isOpen ? 'var(--accent-cyan)' : 'var(--status-coral)')}`
                        }}
                      >
                        {completedScreeningsMap[job.id] ? '✓ Screening Completed' : (hasApplied ? '✓ Applied' : (isOpen ? 'Open' : 'Closed'))}
                      </span>
                    </div>

                    {/* Metadata Row: Posted Date & Work Mode */}
                    <div style={{ display: 'flex', gap: '15px', color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '14px', alignItems: 'center' }}>
                      <span>🕒 {daysAgo}</span>
                      <span>•</span>
                      <span>💼 {workMode} · Full Time</span>
                    </div>

                    {/* Key Stats Row: Experience, Salary, Location */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', background: 'rgba(255, 255, 255, 0.02)', padding: '12px', borderRadius: '8px', marginBottom: '16px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                      <div>
                        <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Experience</div>
                        <div style={{ fontSize: '13px', color: '#fff', fontWeight: '600' }}>{experience}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Salary</div>
                        <div style={{ fontSize: '13px', color: 'var(--status-emerald)', fontWeight: '600' }}>{salary}</div>
                      </div>
                    </div>

                    {/* Location Row */}
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                      📍 <strong>Locations:</strong> {location}
                    </div>

                    {/* Skills Badges */}
                    <div>
                      <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '6px' }}>Skills</div>
                      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        {finalRequiredSkills.map((skill, i) => (
                          <span key={i} style={{ background: 'rgba(0, 210, 255, 0.08)', border: '1px solid rgba(0, 210, 255, 0.2)', borderRadius: '4px', padding: '3px 8px', fontSize: '11px', color: '#fff' }}>
                            {skill}
                          </span>
                        ))}
                        {preferredSkills.map((pskill, i) => (
                          <span key={`pref-${i}`} style={{ background: 'rgba(157, 78, 221, 0.1)', border: '1px solid rgba(157, 78, 221, 0.3)', borderRadius: '4px', padding: '3px 8px', fontSize: '11px', color: 'var(--accent-purple)' }}>
                            Good to have {pskill}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
              {jobs.length === 0 && (
                <div className="card-glass" style={{ padding: '40px', textAlign: 'center', gridColumn: 'span 2' }}>
                  <p style={{ color: 'var(--text-secondary)' }}>No positions currently open. Please check back later.</p>
                </div>
              )}
            </div>

            {/* Pagination Controls */}
            {jobs.length > 0 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '25px', padding: '15px 20px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px solid var(--border-glass)' }}>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                  Showing <strong style={{ color: '#fff' }}>{indexOfFirstJob + 1}</strong> - <strong style={{ color: '#fff' }}>{Math.min(indexOfLastJob, jobs.length)}</strong> of <strong style={{ color: '#fff' }}>{jobs.length}</strong> postings
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <button 
                    disabled={currentPage === 1}
                    onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                    className="btn-secondary"
                    style={{ padding: '6px 12px', fontSize: '12px', opacity: currentPage === 1 ? 0.4 : 1, cursor: currentPage === 1 ? 'not-allowed' : 'pointer' }}
                  >
                    ◄ Prev
                  </button>

                  {Array.from({ length: totalPages || 1 }, (_, i) => i + 1).map((pageNum) => (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      style={{
                        padding: '6px 12px',
                        fontSize: '12px',
                        borderRadius: '6px',
                        border: pageNum === currentPage ? '1px solid var(--accent-cyan)' : '1px solid var(--border-glass)',
                        background: pageNum === currentPage ? 'rgba(0, 210, 255, 0.15)' : 'rgba(255,255,255,0.02)',
                        color: pageNum === currentPage ? 'var(--accent-cyan)' : '#fff',
                        cursor: 'pointer',
                        fontWeight: pageNum === currentPage ? '700' : '400'
                      }}
                    >
                      {pageNum}
                    </button>
                  ))}

                  <button 
                    disabled={currentPage === totalPages || totalPages === 0}
                    onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                    className="btn-secondary"
                    style={{ padding: '6px 12px', fontSize: '12px', opacity: (currentPage === totalPages || totalPages === 0) ? 0.4 : 1, cursor: (currentPage === totalPages || totalPages === 0) ? 'not-allowed' : 'pointer' }}
                  >
                    Next ►
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Detailed Drawer & Application Form */}
          {selectedJob && (() => {
            const hasApplied = appliedJobIds.includes(selectedJob.id);
            const isOpen = (selectedJob.status || 'open').toLowerCase() === 'open';
            const company = selectedJob.company_name || 'Implere Technologies';
            const daysAgo = getDaysAgoText(selectedJob.created_at);
            const workMode = (selectedJob.work_mode || 'Onsite').toUpperCase();
            const experience = selectedJob.experience_range || `${selectedJob.parsed_attributes?.minimum_experience_years || '3 - 5'} Years`;
            const salary = selectedJob.salary_range || '₹ 15L - 18L / year';
            const location = selectedJob.location || 'Bangalore';
            const requiredSkills = selectedJob.parsed_attributes?.tech_stack || ['Python', 'Django', 'Flask/FastAPI', 'OOPS', 'MySQL'];
            const preferredSkills = selectedJob.parsed_attributes?.preferred_skills || ['Java'];

            return (
              <div className="card-glass" style={{ padding: '30px', position: 'sticky', top: '0', height: 'fit-content' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '15px' }}>
                  <div>
                    <h2 style={{ fontSize: '24px', color: '#fff', fontWeight: '700', marginBottom: '4px' }}>{selectedJob.title}</h2>
                    <div style={{ fontSize: '15px', color: 'var(--accent-cyan)', fontWeight: '600' }}>{company}</div>
                  </div>
                  <button style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', fontSize: '18px', cursor: 'pointer' }} onClick={() => setSelectedJob(null)}>
                    ✕
                  </button>
                </div>

                <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', alignItems: 'center' }}>
                  <span 
                    style={{ 
                      padding: '4px 10px', 
                      borderRadius: '20px', 
                      fontSize: '11px', 
                      fontWeight: '700',
                      textTransform: 'uppercase',
                      background: isOpen ? 'rgba(0, 210, 255, 0.12)' : 'rgba(255, 51, 102, 0.12)',
                      color: isOpen ? 'var(--accent-cyan)' : 'var(--status-coral)',
                      border: `1px solid ${isOpen ? 'var(--accent-cyan)' : 'var(--status-coral)'}`
                    }}
                  >
                    {isOpen ? 'Open' : 'Closed'}
                  </span>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>🕒 {daysAgo}</span>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>💼 {workMode} · Full Time</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', background: 'rgba(255,255,255,0.03)', padding: '15px', borderRadius: '10px', marginBottom: '25px' }}>
                  <div>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Experience</div>
                    <div style={{ fontSize: '14px', color: '#fff', fontWeight: '600' }}>{experience}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Salary</div>
                    <div style={{ fontSize: '14px', color: 'var(--status-emerald)', fontWeight: '600' }}>{salary}</div>
                  </div>
                  <div style={{ gridColumn: 'span 2' }}>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Location</div>
                    <div style={{ fontSize: '13px', color: '#fff', fontWeight: '500' }}>📍 {location}</div>
                  </div>
                </div>

                <div style={{ marginBottom: '25px' }}>
                  <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--accent-cyan)', marginBottom: '10px', letterSpacing: '0.05em' }}>Required Skills</h4>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {requiredSkills.map((tech, i) => (
                      <span key={i} style={{ background: 'rgba(0, 210, 255, 0.08)', border: '1px solid rgba(0, 210, 255, 0.2)', borderRadius: '6px', padding: '5px 12px', fontSize: '12px', color: '#fff' }}>
                        {tech}
                      </span>
                    ))}
                    {preferredSkills.map((ptech, i) => (
                      <span key={`pref-${i}`} style={{ background: 'rgba(157, 78, 221, 0.1)', border: '1px solid rgba(157, 78, 221, 0.3)', borderRadius: '6px', padding: '5px 12px', fontSize: '12px', color: 'var(--accent-purple)' }}>
                        Good to have {ptech}
                      </span>
                    ))}
                  </div>
                </div>

                <div style={{ marginBottom: '30px' }}>
                  <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--accent-cyan)', marginBottom: '10px', letterSpacing: '0.05em' }}>Job Description</h4>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.6', maxHeight: '180px', overflowY: 'auto' }}>
                    {selectedJob.raw_text}
                  </p>
                </div>

                <div style={{ borderTop: '1px solid var(--border-glass)', paddingTop: '25px', textAlign: 'center' }}>
                  {completedScreeningsMap[selectedJob.id] ? (
                    <div>
                      <div style={{ color: 'var(--status-emerald)', fontWeight: '600', fontSize: '15px', marginBottom: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                        <span>✓ Screening Completed</span>
                      </div>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '15px' }}>
                        You have successfully completed the automated voice screening for this position. Applications and retakes are disabled.
                      </p>
                      <button 
                        disabled 
                        className="btn-secondary" 
                        style={{ width: '100%', padding: '12px 0', opacity: 0.5, cursor: 'not-allowed', fontWeight: '600' }}
                      >
                        ✓ Screening Completed
                      </button>
                    </div>
                  ) : hasApplied ? (
                    <div>
                      <div style={{ color: 'var(--accent-cyan)', fontWeight: '600', fontSize: '15px', marginBottom: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                        <span>✓ Application Submitted</span>
                      </div>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '15px' }}>
                        You have applied for this position. Take your interactive voice screening below.
                      </p>
                      <button 
                        className="btn-primary" 
                        onClick={() => onLaunchPortal(selectedJob.id, appliedResumesMap[selectedJob.id] || createdResumeId)}
                        style={{ width: '100%', padding: '12px 0' }}
                      >
                        🎙️ Start Voice Screening
                      </button>
                    </div>
                  ) : (!isOpen ? (
                    <div>
                      <div style={{ color: 'var(--status-coral)', fontWeight: '600', fontSize: '14px', marginBottom: '8px' }}>
                        Applications Closed
                      </div>
                      <button disabled className="btn-secondary" style={{ width: '100%', padding: '12px 0', opacity: 0.5, cursor: 'not-allowed' }}>
                        Closed for Applications
                      </button>
                    </div>
                  ) : (
                    <div>
                      <h3 style={{ fontSize: '15px', color: '#fff', marginBottom: '8px' }}>Apply For This Position</h3>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '18px' }}>
                        Upload your resume PDF/DOCX to complete the parsing screening step.
                      </p>

                      {isUploading ? (
                        <div style={{ color: 'var(--status-amber)', fontWeight: '500' }}>
                          <span className="mono">{uploadProgress}</span>
                        </div>
                      ) : (
                        <label className="btn-primary" style={{ display: 'block', width: '100%', cursor: 'pointer', padding: '12px 0', textAlign: 'center' }}>
                          Upload Resume & Apply
                          <input type="file" accept=".pdf,.docx,.txt" onChange={handleUploadResume} style={{ display: 'none' }} />
                        </label>
                      )}
                    </div>
                  ))}
                </div>

              </div>
            );
          })()}

        </div>
      </div>

    </div>
  );
};

export default CandidateDashboard;
