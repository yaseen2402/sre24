import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, Shield, GitPullRequest } from 'lucide-react';

export default function LandingPage() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // Check if they already have a workspace saved in this browser
  useEffect(() => {
    const savedTenantId = localStorage.getItem('sre24_tenant_id');
    if (savedTenantId) {
      navigate(`/dashboard/${savedTenantId}`);
    }
  }, [navigate]);

  const handleCreateWorkspace = async () => {
    setLoading(true);
    try {
      // Pointing to our FastAPI backend
      const response = await fetch('https://sre24-backend-259813648080.us-central1.run.app/api/tenant/', {
        method: 'POST',
      });
      const data = await response.json();
      
      if (data.tenant_id) {
        // Save the generated ID to browser storage
        localStorage.setItem('sre24_tenant_id', data.tenant_id);
        navigate(`/dashboard/${data.tenant_id}`);
      }
    } catch (error) {
      console.error("Failed to create workspace:", error);
      alert("Backend is not running. Please check the Cloud Run logs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="landing-hero">
      <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginBottom: '2rem' }}>
        <div className="glass-panel" style={{ padding: '20px', borderRadius: '50%' }}>
          <Zap size={32} color="var(--accent-primary)" />
        </div>
        <div className="glass-panel" style={{ padding: '20px', borderRadius: '50%' }}>
          <Shield size={32} color="var(--success)" />
        </div>
        <div className="glass-panel" style={{ padding: '20px', borderRadius: '50%' }}>
          <GitPullRequest size={32} color="var(--accent-secondary)" />
        </div>
      </div>
      
      <h1>Keep the Vibes Going in Production</h1>
      <p style={{ maxWidth: '600px', margin: '0 auto 3rem auto', fontSize: '1.2rem' }}>
        Vibe code with confidence. SRE24 acts as your autonomous safety net intercepting alerts, investigating root causes, and pushing fixes while you sleep.
      </p>
      
      <button 
        className="btn-primary" 
        onClick={handleCreateWorkspace}
        disabled={loading}
        style={{ fontSize: '1.2rem', padding: '16px 40px', minWidth: '200px' }}
      >
        {loading ? <span className="loader"></span> : 'Get Started'}
      </button>
      
    </div>
  );
}
