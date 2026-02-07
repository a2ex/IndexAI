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
import { isAuthenticated as checkAuth, refreshToken, logout as apiLogout, clearAccessToken } from './api/client';
import useWebNotifications from './hooks/useWebNotifications';

export default function App() {
  const [authed, setAuthed] = useState(false);
  const [loading, setLoading] = useState(true);

  useWebNotifications();

  useEffect(() => {
    // On mount, try to restore session via refresh cookie
    refreshToken().then((ok) => {
      setAuthed(ok);
      setLoading(false);
    });
  }, []);

  const handleLogout = async () => {
    await apiLogout();
    setAuthed(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-400 text-sm">Loading...</div>
      </div>
    );
  }

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />;
  }

  return (
    <BrowserRouter>
      <Layout onLogout={handleLogout}>
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
