import React, { useRef, useEffect } from 'react';

const Oscilloscope = ({ status = 'idle', audioAnalyser }) => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationId;
    let phase = 0;

    const resizeCanvas = () => {
      if (canvas.parentElement) {
        canvas.width = canvas.parentElement.clientWidth || 300;
      } else {
        canvas.width = 300;
      }
      canvas.height = 160;
    };
    if (!ctx) return;
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      phase += 0.05;

      if (status === 'muted') {
        // Red Flatline
        ctx.beginPath();
        ctx.moveTo(0, centerY);
        for (let x = 0; x < width; x++) {
          const y = centerY + Math.sin(x * 0.05 + phase) * 2; // slight micro-noise
          ctx.lineTo(x, y);
        }
        ctx.strokeStyle = '#FF3366';
        ctx.shadowColor = '#FF3366';
        ctx.shadowBlur = 10;
        ctx.lineWidth = 3;
        ctx.stroke();
      } else if (status === 'thinking') {
        // Shifting cyan/purple loops
        ctx.shadowBlur = 15;
        ctx.lineWidth = 2.5;
        
        for (let i = 0; i < 3; i++) {
          ctx.beginPath();
          ctx.strokeStyle = i % 2 === 0 ? '#00D2FF' : '#9D4EDD';
          ctx.shadowColor = ctx.strokeStyle;
          
          const offset = i * (Math.PI / 3) + phase * 0.5;
          for (let x = 0; x < width; x++) {
            const progress = x / width;
            const amp = Math.sin(progress * Math.PI) * 25; // fade at edges
            const y = centerY + Math.sin(x * 0.02 + offset) * amp;
            if (x === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          }
          ctx.stroke();
        }
      } else if (status === 'speaking') {
        // Active speaking purple-cyan wave
        ctx.shadowBlur = 12;
        ctx.lineWidth = 3;
        
        const gradient = ctx.createLinearGradient(0, 0, width, 0);
        gradient.addColorStop(0, '#00D2FF');
        gradient.addColorStop(1, '#9D4EDD');
        ctx.strokeStyle = gradient;
        ctx.shadowColor = '#9D4EDD';

        ctx.beginPath();
        for (let x = 0; x < width; x++) {
          const progress = x / width;
          const edgeFade = Math.sin(progress * Math.PI);
          const speechPulse = 1.2 + Math.sin(phase * 1.5) * 0.4;
          const y = centerY + Math.sin(x * 0.035 + phase * 2) * 35 * edgeFade * speechPulse;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      } else if (status === 'listening') {
        // Mint green highly responsive frequency wave
        ctx.strokeStyle = '#00F5D4';
        ctx.shadowColor = '#00F5D4';
        ctx.shadowBlur = 10;
        ctx.lineWidth = 2.5;

        ctx.beginPath();
        if (audioAnalyser) {
          const bufferLength = audioAnalyser.frequencyBinCount;
          const dataArray = new Uint8Array(bufferLength);
          audioAnalyser.getByteTimeDomainData(dataArray);

          const sliceWidth = width / bufferLength;
          let x = 0;

          for (let i = 0; i < bufferLength; i++) {
            const v = dataArray[i] / 128.0;
            const y = v * centerY;

            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);

            x += sliceWidth;
          }
        } else {
          // Mock mic frequency response if no actual device connected
          for (let x = 0; x < width; x++) {
            const progress = x / width;
            const edgeFade = Math.sin(progress * Math.PI);
            // Simulate random spikes and speech energy
            const noise = Math.sin(x * 0.1 + phase * 4) * Math.cos(x * 0.05 + phase * 2);
            const y = centerY + noise * 30 * edgeFade;
            if (x === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          }
        }
        ctx.stroke();
      } else {
        // Idle (Flatline with soft breathing)
        ctx.beginPath();
        ctx.moveTo(0, centerY);
        ctx.strokeStyle = 'rgba(157, 78, 221, 0.4)';
        ctx.shadowColor = '#9D4EDD';
        ctx.shadowBlur = 5;
        ctx.lineWidth = 2;

        for (let x = 0; x < width; x++) {
          const progress = x / width;
          const edgeFade = Math.sin(progress * Math.PI);
          const y = centerY + Math.sin(x * 0.015 + phase * 0.5) * 4 * edgeFade;
          ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      // Reset shadows
      ctx.shadowBlur = 0;
      animationId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', resizeCanvas);
    };
  }, [status, audioAnalyser]);

  return (
    <div style={{ width: '100%', padding: '10px 0' }} data-testid="oscilloscope-wrapper">
      <canvas ref={canvasRef} style={{ display: 'block', margin: '0 auto' }} />
    </div>
  );
};

export default Oscilloscope;
