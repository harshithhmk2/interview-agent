import React, { useState, useEffect } from 'react';
import Oscilloscope from './Oscilloscope';

const InterviewPortal = ({ token, jobId, resumeId, userFullName, onBack }) => {
  const [inInterview, setInInterview] = useState(false);
  const [micPermission, setMicPermission] = useState('prompt'); // prompt, granted, denied
  const [selectedDevice, setSelectedDevice] = useState('');
  const [devices, setDevices] = useState([]);
  const [calibratingVol, setCalibratingVol] = useState(0);
  const [interviewId, setInterviewId] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(
    'Describe a complex technical system or project you worked on and your role in it.'
  );
  const [questionIndex, setQuestionIndex] = useState(1);
  const [totalQuestions, setTotalQuestions] = useState(5);
  const [oscilloscopeStatus, setOscilloscopeStatus] = useState('idle'); // idle, speaking, listening, muted, thinking
  const [responseText, setResponseText] = useState('');
  const [isManualEdit, setIsManualEdit] = useState(false);
  const isManualEditRef = React.useRef(false);
  const baseTranscriptRef = React.useRef('');
  const latestTranscriptRef = React.useRef('');
  const shouldListenRef = React.useRef(false);
  const [sttSupported, setSttSupported] = useState(true);
  const [isCompleted, setIsCompleted] = useState(false);
  const [isInitializing, setIsInitializing] = useState(false);
  const [timeLeft, setTimeLeft] = useState(60); // 60 seconds response timer
  
  // Audio context for actual oscilloscope hook
  const [audioStream, setAudioStream] = useState(null);
  const [analyser, setAnalyser] = useState(null);

  const baseUrl = import.meta.env.VITE_API_BASE_URL || '';

  useEffect(() => {
    // Populate audio devices
    setDevices([
      { id: 'dev-1', label: 'Default System Microphone' },
      { id: 'dev-2', label: 'High Definition Audio Device (External)' },
      { id: 'dev-3', label: 'Wireless Bluetooth Headset Microphone' }
    ]);
    setSelectedDevice('dev-1');
  }, []);

  const requestMicPermission = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setAudioStream(stream);
      setMicPermission('granted');
      
      // Setup Web Audio API analyser
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyserNode = audioCtx.createAnalyser();
      analyserNode.fftSize = 256;
      source.connect(analyserNode);
      setAnalyser(analyserNode);

      // Simulate volume calibration check
      const interval = setInterval(() => {
        setCalibratingVol(Math.floor(Math.random() * 60) + 20);
      }, 100);

      setTimeout(() => {
        clearInterval(interval);
        setCalibratingVol(0);
      }, 3000);

    } catch (err) {
      console.error(err);
      setMicPermission('denied');
    }
  };

  const playAudioBase64 = (base64String) => {
    if (!base64String) return;
    try {
      const audio = new Audio(`data:audio/wav;base64,${base64String}`);
      audio.play().catch(e => console.log('Audio playback prevented by browser policy:', e));
    } catch (e) {
      console.error('Failed to play TTS audio:', e);
    }
  };

  const [plannedQuestionsList, setPlannedQuestionsList] = useState([]);

  const handleEnterInterview = async () => {
    setIsInitializing(true);
    setOscilloscopeStatus('thinking');

    try {
      if (token && jobId && resumeId) {
        const response = await fetch(`${baseUrl}/api/v1/interviews/sessions`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            job_description_id: jobId,
            resume_id: resumeId
          })
        });

        if (response.ok) {
          const data = await response.json();
          setInterviewId(data.id);
          const plannedQuestions = data.questions || [];
          setPlannedQuestionsList(plannedQuestions);
          if (plannedQuestions.length > 0) {
            setTotalQuestions(plannedQuestions.length);
          }
          if (data.first_question) {
            setCurrentQuestion(data.first_question);
          } else if (plannedQuestions.length > 0 && plannedQuestions[0].question_text) {
            setCurrentQuestion(plannedQuestions[0].question_text);
          }
        }
      }
    } catch (err) {
      console.error('Error starting live interview session:', err);
    } finally {
      setIsInitializing(false);
      setInInterview(true);
      setOscilloscopeStatus('speaking');
      
      setTimeout(() => {
        setOscilloscopeStatus('listening');
      }, 3500);
    }
  };

  const recognitionRef = React.useRef(null);
  const [isListeningSTT, setIsListeningSTT] = useState(false);

  const handleTranscriptChange = (e) => {
    const val = e.target.value;
    setResponseText(val);
    latestTranscriptRef.current = val;
    if (!isManualEditRef.current) {
      isManualEditRef.current = true;
      setIsManualEdit(true);
    }
  };

  const handleResyncSpeech = () => {
    isManualEditRef.current = false;
    setIsManualEdit(false);
    baseTranscriptRef.current = responseText;
    latestTranscriptRef.current = responseText;
  };

  // Web Speech API - Continuous Real-time Speech-to-Text Engine
  useEffect(() => {
    shouldListenRef.current = (oscilloscopeStatus === 'listening');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSttSupported(false);
      return;
    }

    setSttSupported(true);

    if (oscilloscopeStatus === 'listening') {
      let isComponentActive = true;

      const startRecognition = () => {
        if (!shouldListenRef.current || !isComponentActive) return;

        try {
          const recognition = new SpeechRecognition();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = 'en-US';

          recognition.onstart = () => {
            if (isComponentActive) setIsListeningSTT(true);
          };

          recognition.onresult = (event) => {
            let sessionTranscript = '';
            for (let i = 0; i < event.results.length; ++i) {
              sessionTranscript += event.results[i][0].transcript;
            }

            const combined = (baseTranscriptRef.current + ' ' + sessionTranscript).replace(/\s+/g, ' ').trim();
            if (combined && !isManualEditRef.current && isComponentActive) {
              setResponseText(combined);
              latestTranscriptRef.current = combined;
            }
          };

          recognition.onerror = (event) => {
            console.warn('SpeechRecognition error:', event.error);
          };

          recognition.onend = () => {
            if (isComponentActive) setIsListeningSTT(false);

            if (latestTranscriptRef.current && !isManualEditRef.current) {
              baseTranscriptRef.current = latestTranscriptRef.current;
            }

            // Auto-restart continuous recognition on pauses
            if (shouldListenRef.current && isComponentActive) {
              setTimeout(() => {
                if (shouldListenRef.current && isComponentActive) {
                  startRecognition();
                }
              }, 150);
            }
          };

          recognition.start();
          recognitionRef.current = recognition;
        } catch (err) {
          console.warn('Failed to start SpeechRecognition:', err);
        }
      };

      startRecognition();

      return () => {
        isComponentActive = false;
        if (recognitionRef.current) {
          try {
            recognitionRef.current.stop();
          } catch (e) {}
          recognitionRef.current = null;
        }
        setIsListeningSTT(false);
      };
    } else {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
        recognitionRef.current = null;
      }
      setIsListeningSTT(false);
    }
  }, [oscilloscopeStatus]);

  const handleSubmitAnswer = async (isTimeout = false) => {
    shouldListenRef.current = false;
    // Stop STT recognition on turn submit
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
      recognitionRef.current = null;
    }

    const finalAnswer = responseText.trim() || (isTimeout ? 'Candidate provided no verbal response within stipulated time.' : '');
    if (!isTimeout && !finalAnswer) return;

    setOscilloscopeStatus('thinking');

    try {
      if (token && interviewId) {
        const response = await fetch(`${baseUrl}/api/v1/interviews/${interviewId}/turns`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            response_text: finalAnswer,
            latency_seconds: 3.5
          })
        });

        if (response.ok) {
          const data = await response.json();
          if (data.is_last || !data.next_question) {
            setIsCompleted(true);
            setOscilloscopeStatus('idle');
            return;
          }

          setQuestionIndex(prev => prev + 1);
          setResponseText('');
          baseTranscriptRef.current = '';
          latestTranscriptRef.current = '';
          isManualEditRef.current = false;
          setIsManualEdit(false);
          setCurrentQuestion(data.next_question);
          if (data.next_question_audio_base64) {
            playAudioBase64(data.next_question_audio_base64);
          }
          setOscilloscopeStatus('speaking');

          setTimeout(() => {
            setOscilloscopeStatus('listening');
          }, 3500);
          return;
        }
      }
    } catch (err) {
      console.error('Error submitting turn:', err);
    }

    // Fallback if offline or LLM generation timed out
    if (questionIndex >= totalQuestions) {
      setIsCompleted(true);
      setOscilloscopeStatus('idle');
    } else {
      const nextIdx = questionIndex; // questionIndex is 1-based index pointing to next question
      if (plannedQuestionsList.length > nextIdx && plannedQuestionsList[nextIdx].question_text) {
        setCurrentQuestion(plannedQuestionsList[nextIdx].question_text);
      }
      setQuestionIndex(prev => prev + 1);
      setResponseText('');
      baseTranscriptRef.current = '';
      latestTranscriptRef.current = '';
      isManualEditRef.current = false;
      setIsManualEdit(false);
      setOscilloscopeStatus('speaking');
      setTimeout(() => {
        setOscilloscopeStatus('listening');
      }, 3500);
    }
  };

  // Ref to prevent stale closures in interval
  const handleSubmitAnswerRef = React.useRef();
  handleSubmitAnswerRef.current = handleSubmitAnswer;

  // Question response timer logic - AUTO-SUBMIT on stipulated time expiration
  useEffect(() => {
    let timer = null;
    if (oscilloscopeStatus === 'listening') {
      setTimeLeft(60);
      timer = setInterval(() => {
        setTimeLeft(prev => {
          if (prev <= 1) {
            clearInterval(timer);
            // Auto submit response recorded during stipulated time and ask next question
            if (handleSubmitAnswerRef.current) {
              handleSubmitAnswerRef.current(true);
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      setTimeLeft(60);
    }

    return () => {
      if (timer) clearInterval(timer);
    };
  }, [oscilloscopeStatus]);

  const handleToggleMute = () => {
    if (oscilloscopeStatus === 'muted') {
      setOscilloscopeStatus('listening');
    } else if (oscilloscopeStatus === 'listening') {
      setOscilloscopeStatus('muted');
    }
  };

  useEffect(() => {
    return () => {
      if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
      }
    };
  }, [audioStream]);

  if (isCompleted) {
    return (
      <div className="page-view" style={{ maxWidth: '600px', margin: '60px auto', padding: '20px' }}>
        <div className="card-glass" style={{ padding: '40px', textAlign: 'center' }}>
          <h2 style={{ fontSize: '28px', color: '#00F5D4', marginBottom: '20px' }}>Interview Completed!</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '30px', lineHeight: '1.6' }}>
            Thank you for completing the voice screening. Your responses have been transcribed, evaluated, and compiled into a recruiter report.
          </p>
          <button className="btn-primary" onClick={onBack}>Return to Portal</button>
        </div>
      </div>
    );
  }

  if (!inInterview) {
    // Calibration screen
    return (
      <div className="page-view" style={{ maxWidth: '650px', margin: '40px auto', padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
          <h1 style={{ color: '#fff', fontSize: '24px' }}>Candidate Setup & Calibration</h1>
          <button className="btn-secondary" onClick={onBack}>Cancel</button>
        </div>

        <div className="card-glass" style={{ padding: '30px' }}>
          <h2 style={{ fontSize: '18px', color: 'var(--accent-cyan)', marginBottom: '15px' }}>Step 1: Microphone Permission</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '20px' }}>
            We need permission to access your microphone so the AI interviewer can hear and transcribe your answers.
          </p>

          {micPermission !== 'granted' ? (
            <button className="btn-primary" onClick={requestMicPermission} style={{ marginBottom: '30px' }}>
              Grant Mic Access
            </button>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#00F5D4', marginBottom: '30px', fontWeight: '500' }}>
              <span style={{ fontSize: '20px' }}>✔</span> Mic Access Granted
            </div>
          )}

          {micPermission === 'granted' && (
            <div className="page-view">
              <h2 style={{ fontSize: '18px', color: 'var(--accent-cyan)', marginBottom: '15px' }}>Step 2: Device Selection & Level Test</h2>
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>Input Device</label>
                <select 
                  value={selectedDevice} 
                  onChange={(e) => setSelectedDevice(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px',
                    borderRadius: '8px',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid var(--border-glass)',
                    color: '#fff',
                    outline: 'none'
                  }}
                >
                  {devices.map(d => (
                    <option key={d.id} value={d.id} style={{ background: '#0E0E1B' }}>{d.label}</option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: '30px' }}>
                <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                  Microphone Input Level Check
                </label>
                <div style={{ width: '100%', height: '10px', background: 'rgba(255,255,255,0.05)', borderRadius: '5px', overflow: 'hidden' }}>
                  <div 
                    style={{ 
                      width: `${calibratingVol}%`, 
                      height: '100%', 
                      background: 'var(--gradient-primary)', 
                      transition: 'width 100ms ease' 
                    }} 
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  <span>Silent</span>
                  <span>Ideal Level</span>
                  <span>Loud</span>
                </div>
              </div>

              <button className="btn-primary" onClick={handleEnterInterview} style={{ width: '100%' }}>
                Enter Interview Room
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Active Interview Session
  return (
    <div className="page-view" style={{ maxWidth: '800px', margin: '40px auto', padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <h2 style={{ fontSize: '20px', color: '#fff' }}>Voice Interview Room</h2>
        <div style={{ display: 'flex', gap: '15px', alignItems: 'center', fontSize: '13px', color: 'var(--text-secondary)' }}>
          <span style={{ color: '#00F5D4' }}>● Live Connection Good</span>
          <span>Question {questionIndex} of {totalQuestions}</span>
        </div>
      </div>

      <div className="card-glass" style={{ padding: '30px', marginBottom: '30px', position: 'relative' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--accent-purple)', fontWeight: '600' }}>
            AI Assistant Interviewer
          </span>
          {oscilloscopeStatus === 'speaking' && <span style={{ fontSize: '12px', color: 'var(--accent-cyan)' }}>Speaking...</span>}
          {oscilloscopeStatus === 'listening' && <span style={{ fontSize: '12px', color: '#00F5D4' }}>Listening...</span>}
          {oscilloscopeStatus === 'muted' && <span style={{ fontSize: '12px', color: 'var(--status-coral)' }}>Muted</span>}
          {oscilloscopeStatus === 'thinking' && <span style={{ fontSize: '12px', color: 'var(--status-amber)' }}>Processing Response...</span>}
        </div>
        <h2 style={{ fontSize: '20px', lineHeight: '1.5', color: '#fff', marginBottom: '25px' }}>
          {currentQuestion}
        </h2>
        {(oscilloscopeStatus === 'listening' || oscilloscopeStatus === 'muted') && (
          <div style={{ marginTop: '15px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
              <span>Time remaining to respond:</span>
              <span style={{ color: timeLeft <= 10 ? 'var(--status-coral)' : 'var(--accent-cyan)', fontWeight: 'bold' }}>
                {timeLeft}s
              </span>
            </div>
            <div style={{ width: '100%', height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
              <div 
                style={{ 
                  width: `${(timeLeft / 60) * 100}%`, 
                  height: '100%', 
                  background: timeLeft <= 10 ? 'var(--status-coral)' : 'var(--accent-cyan)', 
                  transition: 'width 1s linear' 
                }} 
              />
            </div>
          </div>
        )}
      </div>

      <div className="card-glass" style={{ padding: '25px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Oscilloscope status={oscilloscopeStatus} audioAnalyser={analyser} />

        <div style={{ width: '100%', margin: '20px 0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Candidate Transcript Input
            </label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {isManualEdit ? (
                <>
                  <span style={{ fontSize: '11px', color: '#FFD166', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    ✏️ Transcript Edited (Speech overwrite paused)
                  </span>
                  <button
                    type="button"
                    onClick={handleResyncSpeech}
                    style={{
                      background: 'rgba(255, 209, 102, 0.1)',
                      border: '1px solid rgba(255, 209, 102, 0.3)',
                      color: '#FFD166',
                      borderRadius: '4px',
                      padding: '2px 8px',
                      fontSize: '11px',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                    title="Click to resume real-time voice speech-to-text overwriting"
                  >
                    🔄 Resume Speech Sync
                  </button>
                </>
              ) : (
                isListeningSTT && (
                  <span style={{ fontSize: '11px', color: '#00F5D4', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#00F5D4', display: 'inline-block' }} />
                    🎙️ Live STT Active (Transcribing speech in real time...)
                  </span>
                )
              )}
              {!sttSupported && (
                <span style={{ fontSize: '11px', color: 'var(--status-amber)', fontWeight: '500' }}>
                  ℹ️ Real-time speech transcription unavailable in this browser. Type your answer directly.
                </span>
              )}
            </div>
          </div>
          <textarea
            value={responseText}
            onChange={handleTranscriptChange}
            placeholder={
              oscilloscopeStatus === 'listening' 
                ? "Speak into your microphone for real-time transcription, or type/edit your answer directly here..." 
                : "Waiting for AI..."
            }
            disabled={oscilloscopeStatus !== 'listening' && oscilloscopeStatus !== 'muted'}
            style={{
              width: '100%',
              height: '110px',
              padding: '14px',
              borderRadius: '10px',
              background: 'rgba(255,255,255,0.03)',
              border: isManualEdit 
                ? '1px solid #FFD166' 
                : (isListeningSTT ? '1px solid #00F5D4' : '1px solid var(--border-glass)'),
              color: '#fff',
              outline: 'none',
              resize: 'none',
              fontSize: '14px',
              lineHeight: '1.5',
              boxShadow: isManualEdit 
                ? '0 0 12px rgba(255, 209, 102, 0.2)' 
                : (isListeningSTT ? '0 0 12px rgba(0, 245, 212, 0.25)' : 'none'),
              transition: 'all 0.3s ease'
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px' }}>
            <span>
              Words: <strong style={{ color: '#fff' }}>{responseText.trim() ? responseText.trim().split(/\s+/).length : 0}</strong> | Characters: <strong style={{ color: '#fff' }}>{responseText.length}</strong>
            </span>
            <span>
              💡 You can edit or refine the transcribed text in the text area before submitting your response.
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '15px', justifyContent: 'center' }}>
          <button 
            className="btn-secondary" 
            onClick={handleToggleMute}
            style={{
              borderColor: oscilloscopeStatus === 'muted' ? 'var(--status-coral)' : 'var(--border-glass)',
              color: oscilloscopeStatus === 'muted' ? 'var(--status-coral)' : 'var(--text-primary)'
            }}
          >
            {oscilloscopeStatus === 'muted' ? 'Unmute Mic' : 'Mute Mic'}
          </button>
          
          <button 
            className="btn-primary" 
            onClick={handleSubmitAnswer}
            disabled={(oscilloscopeStatus !== 'listening' && oscilloscopeStatus !== 'muted') || !responseText.trim()}
            style={{
              opacity: ((oscilloscopeStatus !== 'listening' && oscilloscopeStatus !== 'muted') || !responseText.trim()) ? 0.5 : 1
            }}
          >
            Submit Answer
          </button>
        </div>
      </div>
    </div>
  );
};

export default InterviewPortal;
