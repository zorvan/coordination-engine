import { Link, NavLink, Route, Routes } from 'react-router-dom'
import {
  DashboardPage,
  InvitationsPage,
  MatchPage,
  MyGatheringsPage,
  ProfilePage,
  SettingsPage,
} from '@presentation/pages'

type AppShellProps = {
  onLogout: () => void
}

export function AppShell({ onLogout }: AppShellProps) {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="logo">CE</div>
        <nav>
          <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/">Dashboard</NavLink>
          <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/gatherings">My Gatherings</NavLink>
          <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/invitations">Invitations <span className="badge">3</span></NavLink>
          <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/profile">Profile</NavLink>
          <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/settings">Settings</NavLink>
          <button className="sidebar-logout" type="button" onClick={onLogout}>Logout</button>
        </nav>
      </aside>

      <div className="content-shell">
        <header className="topbar">
          <h1>Coordination Engine</h1>
          <input aria-label="Global Search" placeholder="Search gatherings, members, circles..." />
          <div className="top-actions">
            <button type="button" className="icon-btn" aria-label="Notifications">🔔<span className="dot">4</span></button>
            <button type="button" className="avatar-btn" aria-label="Profile menu">ZA</button>
          </div>
        </header>

        <main className="page">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/matches/:matchId" element={<MatchPage />} />
            <Route path="/gatherings" element={<MyGatheringsPage />} />
            <Route path="/invitations" element={<InvitationsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<div className="panel"><p>Page not found. <Link to="/">Go to dashboard</Link>.</p></div>} />
          </Routes>
        </main>

        <nav className="mobile-tabs">
          <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/">Dashboard</NavLink>
          <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/gatherings">Gatherings</NavLink>
          <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/invitations">Invites</NavLink>
          <NavLink className={({ isActive }) => (isActive ? 'active' : '')} to="/profile">Profile</NavLink>
        </nav>
      </div>
    </div>
  )
}
