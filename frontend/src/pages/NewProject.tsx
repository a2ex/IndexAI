import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createProject, getCredits } from '../api/client';
import { useEffect } from 'react';

export default function NewProject() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [urlsText, setUrlsText] = useState('');
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getCredits().then((c) => setCredits(c.balance)).catch(() => {});
  }, []);

  const urls = urlsText
    .split('\n')
    .map((u) => u.trim())
    .filter((u) => u.length > 0 && u.startsWith('http'));

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      setUrlsText(ev.target?.result as string);
    };
    reader.readAsText(file);
  };

  const handleSubmit = async () => {
    if (!name.trim() || urls.length === 0) return;
    if (urls.length > credits) {
      setError(`Not enough credits. You have ${credits}, need ${urls.length}`);
      return;
    }

    setLoading(true);
    setError('');
    try {
      const project = await createProject({ name: name.trim(), urls });
      navigate(`/projects/${project.id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">New Project</h2>
        <p className="text-sm text-slate-500 mt-1">Submit URLs for indexation</p>
      </div>

      <div className="bg-slate-900 rounded-xl border border-slate-800 p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">Project Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My SEO Project"
            className="w-full border border-slate-700 bg-slate-800 text-white placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            URLs (one per line)
          </label>
          <textarea
            value={urlsText}
            onChange={(e) => setUrlsText(e.target.value)}
            placeholder={"https://example.com/page1\nhttps://example.com/page2\nhttps://example.com/page3"}
            rows={10}
            className="w-full border border-slate-700 bg-slate-800 text-white placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
          />
          <div className="flex items-center justify-between mt-2">
            <label className="text-sm text-cyan-400 hover:underline cursor-pointer">
              Or upload a CSV/TXT file
              <input
                type="file"
                accept=".csv,.txt"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          </div>
        </div>

        <div className="bg-slate-800 rounded-lg p-4 flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-300">
              <span className="font-bold text-lg">{urls.length}</span> URLs to submit
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Cost: {urls.length} credits | Your balance: {credits} credits
            </p>
          </div>
          {urls.length > credits && (
            <span className="text-xs text-rose-400 font-medium">Insufficient credits</span>
          )}
        </div>

        {error && (
          <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm rounded-lg p-3">{error}</div>
        )}

        <button
          onClick={handleSubmit}
          disabled={loading || !name.trim() || urls.length === 0 || urls.length > credits}
          className="w-full bg-cyan-500 text-slate-950 py-3 rounded-lg text-sm font-medium hover:bg-cyan-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Submitting...' : `Submit ${urls.length} URLs for Indexation`}
        </button>
      </div>
    </div>
  );
}
