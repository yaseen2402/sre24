import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, CheckCircle, XCircle, Cloud, GitBranch, Database, Save, X } from 'lucide-react';

export default function Settings() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState({});

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/config');
      const data = await res.json();
      setConfig(data);
    } catch (e) {
      console.error('Failed to fetch config', e);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (integrationName) => {
    setEditing(integrationName);
    setFormData({}); // Reset form
  };

  const handleSave = async () => {
    try {
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      setEditing(null);
      await fetchConfig();
    } catch (e) {
      console.error('Failed to save', e);
    }
  };

  if (loading) return <div className="container" style={{ textAlign: 'center', marginTop: '4rem' }}>Loading settings...</div>;

  const integrations = [
    { 
      name: 'Dynatrace', 
      icon: <Database size={24} />, 
      status: config.dt_platform_token_set ? 'connected' : 'disconnected', 
      description: 'Application Performance Monitoring',
      fields: [
        { key: 'dt_environment', label: 'Environment URL', placeholder: config.dt_environment || 'https://xxx.apps.dynatrace.com' },
        { key: 'dt_platform_token', label: 'Platform Token', placeholder: config.dt_platform_token_set ? '••••••••••••••••' : 'Enter token' }
      ]
    },
    { 
      name: 'Google Cloud Platform', 
      icon: <Cloud size={24} />, 
      status: config.gcp_project_id ? 'connected' : 'disconnected', 
      description: 'Cloud Infrastructure & IAM',
      fields: [
        { key: 'gcp_project_id', label: 'Project ID', placeholder: config.gcp_project_id || 'my-project-id' },
        { key: 'gcp_region', label: 'Region', placeholder: config.gcp_region || 'us-central1' }
      ]
    },
    { 
      name: 'GitHub', 
      icon: <GitBranch size={24} />, 
      status: config.github_token_set ? 'connected' : 'disconnected', 
      description: 'Source Control & GitHub Actions',
      fields: [
        { key: 'github_repo', label: 'Target Repository', placeholder: config.github_repo || 'owner/repo' },
        { key: 'github_token', label: 'Personal Access Token', placeholder: config.github_token_set ? '••••••••••••••••' : 'Enter token' }
      ]
    }
  ];

  return (
    <div className="container">
      <div className="section-header">
        <h2 className="section-title"><SettingsIcon /> Integrations & Settings</h2>
      </div>

      <div className="dashboard-grid">
        {integrations.map((integration, i) => (
          <div key={i} className="glass stats-card" style={{ gridColumn: 'span 4' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <div style={{ padding: '0.75rem', background: 'rgba(255,255,255,0.05)', borderRadius: '12px' }}>
                {integration.icon}
              </div>
              {integration.status === 'connected' ? (
                <span className="badge badge-success" style={{ display: 'flex', gap: '0.25rem' }}>
                  <CheckCircle size={12} /> Connected
                </span>
              ) : (
                <span className="badge badge-danger" style={{ display: 'flex', gap: '0.25rem' }}>
                  <XCircle size={12} /> Disconnected
                </span>
              )}
            </div>
            
            <h3 style={{ fontSize: '1.1rem', marginBottom: '0.25rem', margin: 0 }}>{integration.name}</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
              {integration.description}
            </p>

            {editing === integration.name ? (
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '8px', marginBottom: '1rem' }}>
                {integration.fields.map(field => (
                  <div key={field.key} style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                      {field.label}
                    </label>
                    <input 
                      type="text" 
                      placeholder={field.placeholder}
                      style={{ 
                        width: '100%', 
                        padding: '0.5rem', 
                        background: 'rgba(255,255,255,0.05)', 
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '4px',
                        color: 'white'
                      }}
                      onChange={(e) => setFormData({...formData, [field.key]: e.target.value})}
                    />
                  </div>
                ))}
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button onClick={handleSave} className="btn btn-primary" style={{ flex: 1, display: 'flex', justifyContent: 'center', gap: '0.25rem' }}>
                    <Save size={16} /> Save
                  </button>
                  <button onClick={() => setEditing(null)} className="btn btn-outline" style={{ display: 'flex', justifyContent: 'center', padding: '0.5rem' }}>
                    <X size={16} />
                  </button>
                </div>
              </div>
            ) : (
              <button 
                className="btn btn-outline" 
                style={{ width: '100%' }}
                onClick={() => handleEdit(integration.name)}
              >
                Configure
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
