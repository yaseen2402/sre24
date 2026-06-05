import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, ArrowRight, Play } from 'lucide-react';

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="container hero">
      <Shield size={64} color="var(--primary)" style={{ marginBottom: '2rem' }} />
      <h1>Autonomous SRE Agent</h1>
      <p>Self-healing infrastructure powered by AI. Detect, analyze, and resolve production incidents in real-time with zero human intervention.</p>
      
      <div className="hero-btns">
        <button className="btn btn-primary" onClick={() => navigate('/dashboard')}>
          Get Started <ArrowRight size={18} />
        </button>
        <button className="btn btn-outline" onClick={() => navigate('/dashboard')}>
          Try Demo <Play size={18} />
        </button>
      </div>
    </div>
  );
}
