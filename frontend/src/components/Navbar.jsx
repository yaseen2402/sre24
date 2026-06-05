import React from 'react';
import { NavLink } from 'react-router-dom';
import { Activity, ShieldAlert, Settings, LayoutDashboard } from 'lucide-react';

export default function Navbar() {
  return (
    <nav className="navbar">
      <NavLink to="/" className="nav-brand" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 'bold', fontSize: '1.25rem' }}>
        <Activity color="var(--primary)" />
        <span>AutoSRE Agent</span>
      </NavLink>
      <div className="nav-links">
        <NavLink to="/dashboard" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
          <LayoutDashboard size={18} />
          Dashboard
        </NavLink>
        <NavLink to="/incidents" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
          <ShieldAlert size={18} />
          Incidents
        </NavLink>
        <NavLink to="/settings" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
          <Settings size={18} />
          Settings
        </NavLink>
      </div>
    </nav>
  );
}
