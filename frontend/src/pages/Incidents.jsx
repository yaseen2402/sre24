import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { RefreshCw, Activity, GitPullRequest, CheckCircle2, Search } from 'lucide-react';

export default function Incidents() {
  const { tenantId } = useParams();
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchIncidents = useCallback(async () => {
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
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    if (tenantId) {
      fetchIncidents();
    }
  }, [tenantId, fetchIncidents]);

  if (loading) return <div className="landing-hero"><div className="loader"></div></div>;

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', width: '100%' }}>
      <div className="glass-panel" style={{ marginTop: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
            <Activity size={24} color="var(--accent-secondary)" />
            Incident History
          </h2>
          <button onClick={fetchIncidents} disabled={refreshing} className="btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <RefreshCw size={16} className={refreshing ? 'spinning' : ''} />
            Refresh
          </button>
        </div>

        {incidents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '4rem 0' }}>
            <Activity size={48} color="rgba(255,255,255,0.1)" style={{ marginBottom: '1rem' }} />
            <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>
              No incidents intercepted yet. Waiting for Dynatrace webhooks...
            </p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-glass)' }}>
                  <th style={{ padding: '16px', color: 'var(--text-secondary)', fontWeight: 500 }}>Time</th>
                  <th style={{ padding: '16px', color: 'var(--text-secondary)', fontWeight: 500 }}>Problem ID</th>
                  <th style={{ padding: '16px', color: 'var(--text-secondary)', fontWeight: 500 }}>Status</th>
                  <th style={{ padding: '16px', color: 'var(--text-secondary)', fontWeight: 500 }}>Autonomous Action</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map(inc => (
                  <tr key={inc.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', transition: 'background 0.2s' }} className="hover-row">
                    <td style={{ padding: '16px', color: 'var(--text-primary)' }}>{new Date(inc.created_at).toLocaleString()}</td>
                    <td style={{ padding: '16px', color: 'var(--accent-primary)', fontWeight: 500 }}>{inc.dynatrace_problem_id}</td>
                    <td style={{ padding: '16px' }}>
                      <span className={`badge ${inc.status === 'FAILED' ? 'danger' : ''} ${inc.status === 'PROCESSING' ? 'warning' : 'success'}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        {inc.status === 'RESOLVED' && <CheckCircle2 size={12} />}
                        {inc.status}
                      </span>
                    </td>
                    <td style={{ padding: '16px' }}>
                      {inc.pr_url ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.9rem' }}>
                              <CheckCircle2 size={16} /> Patch Created
                            </span>
                            <a href={inc.pr_url} target="_blank" rel="noreferrer" className="btn-secondary" style={{ padding: '4px 12px', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px', textDecoration: 'none' }}>
                              <GitPullRequest size={14} /> Review PR
                            </a>
                          </div>
                          {inc.agent_logs && (
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                              <strong>AI Summary:</strong> {inc.agent_logs.length > 150 ? inc.agent_logs.substring(0, 150) + '...' : inc.agent_logs}
                            </div>
                          )}
                        </div>
                      ) : inc.agent_logs ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
                          <Search size={16} />
                          <span style={{ fontSize: '0.85rem' }}>{inc.agent_logs.substring(0, 60)}...</span>
                        </div>
                      ) : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--warning)' }}>
                          <Activity size={16} className="spinning" />
                          <span style={{ fontSize: '0.9rem' }}>Investigating Root Cause...</span>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
