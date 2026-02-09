import { useState } from 'react';
import { login, register } from '../api/client';

interface Props {
  onLogin: () => void;
}

export default function Login({ onLogin }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email.trim() || !password) return;
    setLoading(true);
    setError('');
    try {
      await login(email.trim(), password);
      onLogin();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!email.trim() || !password) return;
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await register(email.trim(), password);
      onLogin();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = mode === 'login' ? handleLogin : handleRegister;

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-white mb-2">IndexAI</h1>
        <p className="text-slate-500 text-sm mb-6">SEO Indexation Service</p>

        <div className="flex gap-2 mb-6">
          <button
            onClick={() => { setMode('login'); setError(''); }}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
              mode === 'login' ? 'bg-cyan-500 text-slate-950' : 'bg-slate-800 text-slate-400'
            }`}
          >
            Login
          </button>
          <button
            onClick={() => { setMode('register'); setError(''); }}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
              mode === 'register' ? 'bg-cyan-500 text-slate-950' : 'bg-slate-800 text-slate-400'
            }`}
          >
            Register
          </button>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full border border-slate-700 bg-slate-800 text-white placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          />

          <label className="block text-sm font-medium text-slate-300 mb-1">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full border border-slate-700 bg-slate-800 text-white placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          />

          {mode === 'register' && (
            <>
              <label className="block text-sm font-medium text-slate-300 mb-1">Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full border border-slate-700 bg-slate-800 text-white placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
                onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              />
            </>
          )}

          {error && <p className="text-rose-400 text-xs mb-3">{error}</p>}

          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full bg-cyan-500 text-slate-950 py-2 rounded-lg text-sm font-medium hover:bg-cyan-400 transition-colors disabled:opacity-50"
          >
            {loading
              ? (mode === 'login' ? 'Signing in...' : 'Creating account...')
              : (mode === 'login' ? 'Sign In' : 'Create Account')
            }
          </button>
        </div>
      </div>
    </div>
  );
}
