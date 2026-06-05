import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Settings, Save, CheckCircle2, Copy, RefreshCw, Activity } from 'lucide-react';

export default function Dashboard() {
  const { tenantId } = useParams();
  const [config, setConfig] = useState({
    name: 'My Workspace',
    dt_environment: '',
    github_repo: '',
    gcp_project: '',
    dt_platform_token: '',
    github_token: ''
  });
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);

  const webhookUrl = `https://sre24-backend-259813648080.us-central1.run.app/webhook/${tenantId}`;

  const fetchIncidents = useCallback(async () => {
    // Save this tenantId to browser storage so Landing Page knows who we are
    if (tenantId) {
      localStorage.setItem('sre24_tenant_id', tenantId);
    }
    
    setRefreshing(true);
    try {
      const res = await fetch(`https://sre24-backend-259813648080.us-central1.run.app/api/tenant/${tenantId}/incidents`);
      const data = await res.json();
      if (Array.isArray(data)) {
        setIncidents(data);
      }
    } catch (err) {
      console.error("Failed to fetch incidents", err);
    } finally {
      setRefreshing(false);
    }
  }, [tenantId]);

  useEffect(() => {
    // Fetch initial config
    fetch(`https://sre24-backend-259813648080.us-central1.run.app/api/tenant/${tenantId}`)
      .then(res => res.json())
      .then(data => {
        setConfig(prev => ({ ...prev, ...data }));
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load config", err);
        setLoading(false);
      });
  }, [tenantId]);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await fetch(`https://sre24-backend-259813648080.us-central1.run.app/api/tenant/${tenantId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      if (!res.ok) {
        throw new Error(`Backend rejected save: ${await res.text()}`);
      }
      
      // Instantly update the Connected/Missing labels in the UI
      setConfig(prev => ({
        ...prev,
        has_github_token: prev.github_token ? true : prev.has_github_token,
        has_dt_token: prev.dt_platform_token ? true : prev.has_dt_token
      }));
      alert("Configuration saved successfully!");
    } catch (err) {
      console.error(err);
      alert("Failed to save configuration");
    } finally {
      setSaving(false);
    }
  };

  const copyWebhook = () => {
    navigator.clipboard.writeText(webhookUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) return <div className="landing-hero"><div className="loader"></div></div>;

  return (
    <>
      <div className="dashboard-grid">
        
        {/* Left Column: Instructions */}
        <div className="glass-panel" style={{ height: 'fit-content' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Settings size={24} color="var(--accent-primary)" />
            Setup Instructions
          </h2>
          
          <div style={{ marginBottom: '2rem' }}>
            <h3 style={{ fontSize: '1rem', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>1. Your Unique Webhook URL</h3>
            <p style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>
              Paste this exact URL into your Dynatrace Problem Notifications settings.
            </p>
            <div className="copy-box">
              <code>{webhookUrl}</code>
              <button className="btn-secondary" onClick={copyWebhook} style={{ padding: '6px 12px' }}>
                {copied ? <CheckCircle2 size={16} color="var(--success)" /> : <Copy size={16} />}
              </button>
            </div>
          </div>

          <div>
            <h3 style={{ fontSize: '1rem', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>2. Integrations</h3>
            <p style={{ fontSize: '0.9rem' }}>
              Provide your tokens so SRE24 can read alerts and push code fixes directly to your repository.
            </p>
            <ul style={{ listStyle: 'none', marginTop: '1rem' }}>
              <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                <span className={`badge ${config.has_dt_token ? '' : 'danger'}`}>
                  {config.has_dt_token ? 'Connected' : 'Missing'}
                </span> Dynatrace
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}>
                <span className={`badge ${config.has_github_token ? '' : 'danger'}`}>
                  {config.has_github_token ? 'Connected' : 'Missing'}
                </span> GitHub
              </li>
            </ul>
          </div>
        </div>

        {/* Right Column: Form */}
        <div className="glass-panel">
          <h2 style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            Project Configuration
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 'normal' }}>ID: {tenantId}</span>
          </h2>

          <form onSubmit={handleSave}>
            <div className="form-group">
              <label className="form-label">Project Name</label>
              <input 
                type="text" 
                className="form-input" 
                value={config.name || ''} 
                onChange={e => setConfig({...config, name: e.target.value})} 
                required
              />
            </div>

            <hr style={{ border: 'none', borderTop: '1px solid var(--border-glass)', margin: '2rem 0' }} />
            <h3 style={{ marginBottom: '1.5rem', color: 'var(--accent-primary)' }}>GitHub Integration</h3>

            <div className="form-group">
              <label className="form-label">Target Repository (owner/repo)</label>
              <input 
                type="text" 
                className="form-input" 
                placeholder="e.g. yaseen2402/dummy_app"
                value={config.github_repo || ''} 
                onChange={e => setConfig({...config, github_repo: e.target.value})} 
              />
            </div>

            <div className="form-group">
              <label className="form-label">GitHub Personal Access Token</label>
              <input 
                type="password" 
                className="form-input" 
                placeholder={config.has_github_token ? "•••••••••••• (Token Saved)" : "ghp_..."}
                onChange={e => setConfig({...config, github_token: e.target.value})} 
              />
            </div>

            <hr style={{ border: 'none', borderTop: '1px solid var(--border-glass)', margin: '2rem 0' }} />
            <h3 style={{ marginBottom: '1.5rem', color: 'var(--accent-primary)' }}>Dynatrace Integration</h3>

            <div className="form-group">
              <label className="form-label">Dynatrace Environment URL</label>
              <input 
                type="text" 
                className="form-input" 
                placeholder="https://xyz.apps.dynatrace.com"
                value={config.dt_environment || ''} 
                onChange={e => setConfig({...config, dt_environment: e.target.value})} 
              />
            </div>

            <div className="form-group">
              <label className="form-label">Dynatrace Platform Token</label>
              <input 
                type="password" 
                className="form-input" 
                placeholder={config.has_dt_token ? "•••••••••••• (Token Saved)" : "dt0c01..."}
                onChange={e => setConfig({...config, dt_platform_token: e.target.value})} 
              />
            </div>

            <hr style={{ border: 'none', borderTop: '1px solid var(--border-glass)', margin: '2rem 0' }} />
            <h3 style={{ marginBottom: '1.5rem', color: 'var(--accent-primary)' }}>Google Cloud Integration</h3>

            <div className="form-group">
              <label className="form-label">GCP Project ID</label>
              <input 
                type="text" 
                className="form-input" 
                placeholder="e.g. polish-f9712"
                value={config.gcp_project || ''} 
                onChange={e => setConfig({...config, gcp_project: e.target.value})} 
              />
            </div>

            <div className="form-group">
              <label className="form-label">GCP Region</label>
              <input 
                type="text" 
                className="form-input" 
                placeholder="e.g. us-central1"
                value={config.gcp_region || ''} 
                onChange={e => setConfig({...config, gcp_region: e.target.value})} 
              />
            </div>

            <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'flex-end' }}>
              <button type="submit" className="btn-primary" disabled={saving} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {saving ? <span className="loader" style={{ width: '16px', height: '16px' }}></span> : <Save size={18} />}
                Save Configuration
              </button>
            </div>
          </form>
        </div>

      </div>
    </>
  );
}
