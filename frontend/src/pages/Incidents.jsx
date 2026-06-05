import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { RefreshCw, Activity, GitPullRequest, CheckCircle2, Search } from 'lucide-react';

const IncidentRow = ({ inc }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr 
        onClick={() => setExpanded(!expanded)}
        style={{ borderBottom: expanded ? 'none' : '1px solid rgba(255,255,255,0.05)', transition: 'background 0.2s', cursor: 'pointer' }} 
        className="hover-row"
      >
        <td style={{ padding: '16px 8px', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
          {new Date(inc.created_at).toLocaleString()}
        </td>
        <td style={{ padding: '16px 8px', color: 'var(--accent-primary)', fontWeight: 500 }}>
          {inc.dynatrace_problem_id}
        </td>
        <td style={{ padding: '16px 8px' }}>
          <span className={`badge ${inc.status === 'FAILED' ? 'danger' : ''} ${inc.status === 'PROCESSING' ? 'warning' : 'success'}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            {inc.status === 'RESOLVED' && <CheckCircle2 size={12} />}
            {inc.status}
          </span>
        </td>
        <td style={{ padding: '16px 8px', textAlign: 'right' }}>
          <button 
            style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.9rem', padding: '4px 8px' }}
          >
            {expanded ? 'Hide Details' : 'View Details'}
          </button>
        </td>
      </tr>
      
      <tr style={{ borderBottom: expanded ? '1px solid rgba(255,255,255,0.05)' : 'none' }}>
        <td colSpan="4" style={{ padding: 0 }}>
          <div style={{ 
            maxHeight: expanded ? '1000px' : '0', 
            opacity: expanded ? 1 : 0, 
            overflow: 'hidden', 
            transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)' 
          }}>
            <div style={{ padding: '0 8px 16px 8px' }}>
              <div style={{ padding: '20px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '8px', marginTop: '8px', boxSizing: 'border-box', wordBreak: 'break-word' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {inc.pr_url ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                      <span style={{ color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '1rem', fontWeight: 500 }}>
                        <CheckCircle2 size={18} /> Patch Created
                      </span>
                      <a href={inc.pr_url} target="_blank" rel="noreferrer" className="btn-secondary" style={{ padding: '8px 16px', fontSize: '0.9rem', display: 'inline-flex', alignItems: 'center', gap: '8px', textDecoration: 'none' }}>
                        <GitPullRequest size={16} /> Review Pull Request
                      </a>
                    </div>
                  ) : inc.status === 'PROCESSING' ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--warning)' }}>
                      <Activity size={18} className="spinning" />
                      <span style={{ fontSize: '1rem', fontWeight: 500 }}>Agent investigating root cause...</span>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)' }}>
                      <Search size={18} />
                      <span style={{ fontSize: '1rem', fontWeight: 500 }}>Analysis Complete (No code patch generated)</span>
                    </div>
                  )}
                  
                  {inc.agent_logs && (
                    <div style={{ color: 'var(--text-secondary)', lineHeight: '1.6', fontSize: '0.95rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '1rem' }}>
                      <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '8px', fontSize: '1rem' }}>Autonomous Action Summary</strong>
                      <div style={{ whiteSpace: 'pre-wrap' }}>{inc.agent_logs}</div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </td>
      </tr>
    </>
  );
};

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
    <div style={{ maxWidth: '1000px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
      <div style={{ marginTop: '2rem', padding: '0 20px', boxSizing: 'border-box' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', margin: 0 }}>
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
          <div style={{ width: '100%', overflowX: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', tableLayout: 'fixed' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid rgba(255,255,255,0.1)' }}>
                  <th style={{ padding: '16px 8px', color: 'var(--text-secondary)', fontWeight: 500, width: '20%' }}>Time</th>
                  <th style={{ padding: '16px 8px', color: 'var(--text-secondary)', fontWeight: 500, width: '40%' }}>Problem ID</th>
                  <th style={{ padding: '16px 8px', color: 'var(--text-secondary)', fontWeight: 500, width: '20%' }}>Status</th>
                  <th style={{ padding: '16px 8px', color: 'var(--text-secondary)', fontWeight: 500, width: '20%', textAlign: 'right' }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map(inc => <IncidentRow key={inc.id} inc={inc} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
