import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Activity } from 'lucide-react';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import Incidents from './pages/Incidents';
import './index.css';

function NavBar() {
  const location = useLocation();
  const savedTenantId = localStorage.getItem('sre24_tenant_id');

  // Don't show nav buttons on the landing page if they don't have a workspace
  if (!savedTenantId && location.pathname === '/') {
    return (
      <nav className="nav-bar">
        <Link to="/" className="logo">
          <Activity className="logo-icon" size={28} />
          SRE24
        </Link>
      </nav>
    );
  }

  return (
    <nav className="nav-bar">
      <Link to="/" className="logo">
        <Activity className="logo-icon" size={28} />
        SRE24
      </Link>
      <div style={{ display: 'flex', gap: '1rem' }}>
        <Link 
          to={`/dashboard/${savedTenantId}`} 
          className={location.pathname.includes('/dashboard') ? "btn-primary" : "btn-secondary"} 
          style={{textDecoration: 'none', padding: '8px 16px', fontSize: '0.9rem'}}
        >
          Project Config
        </Link>
        <Link 
          to={`/incidents/${savedTenantId}`} 
          className={location.pathname.includes('/incidents') ? "btn-primary" : "btn-secondary"} 
          style={{textDecoration: 'none', padding: '8px 16px', fontSize: '0.9rem'}}
        >
          Incidents
        </Link>
      </div>
    </nav>
  );
}

function App() {
  return (
    <div className="app-container">
      <NavBar />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard/:tenantId" element={<Dashboard />} />
        <Route path="/incidents/:tenantId" element={<Incidents />} />
      </Routes>
    </div>
  );
}

export default App;
