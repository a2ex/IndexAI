import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import NewProject from './pages/NewProject';
import Credits from './pages/Credits';
import Settings from './pages/Settings';
import Layout from './components/Layout';
import Login from './pages/Login';
import { refreshToken, logout as apiLogout, getMe, type UserProfile } from './api/client';
import useWebNotifications from './hooks/useWebNotifications';

export default function App() {
  const [authed, setAuthed] = useState(false);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useWebNotifications();

  const loadUser = async () => {
    try {
      const profile = await getMe();
      setUser(profile);
    } catch {
      // ignore — user just won't see profile
    }
  };

  useEffect(() => {
    refreshToken().then(async (ok) => {
      setAuthed(ok);
      if (ok) await loadUser();
      setLoading(false);
    });
  }, []);

  const handleLogin = async () => {
    setAuthed(true);
    await loadUser();
  };

  const handleLogout = async () => {
    await apiLogout();
    setAuthed(false);
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-slate-500 text-sm">Loading...</div>
      </div>
    );
  }

  if (!authed) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <BrowserRouter>
      <Layout onLogout={handleLogout} user={user}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/new" element={<NewProject />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/credits" element={<Credits />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
