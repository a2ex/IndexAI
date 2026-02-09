import { useEffect, useState } from 'react';
import { getCredits, getCreditHistory, addCredits } from '../api/client';
import type { CreditTransaction } from '../api/client';

const typeColors: Record<string, string> = {
  purchase: 'text-emerald-400',
  debit: 'text-rose-400',
  refund: 'text-cyan-400',
  bonus: 'text-violet-400',
};

export default function Credits() {
  const [balance, setBalance] = useState(0);
  const [history, setHistory] = useState<CreditTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [addAmount, setAddAmount] = useState(100);

  const loadData = () => {
    Promise.all([getCredits(), getCreditHistory()])
      .then(([c, h]) => {
        setBalance(c.balance);
        setHistory(h);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAdd = async () => {
    if (addAmount <= 0) return;
    const result = await addCredits(addAmount);
    setBalance(result.balance);
    loadData();
  };

  if (loading) return <div className="text-slate-500">Loading...</div>;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Credits</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
          <p className="text-sm text-slate-500">Current Balance</p>
          <p className="text-4xl font-bold text-white mt-2">{balance}</p>
          <p className="text-xs text-slate-500 mt-1">credits available</p>
        </div>

        <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
          <p className="text-sm text-slate-500 mb-3">Add Credits</p>
          <div className="flex gap-2">
            <input
              type="number"
              min={1}
              value={addAmount}
              onChange={(e) => setAddAmount(parseInt(e.target.value) || 0)}
              className="flex-1 border border-slate-700 bg-slate-800 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
            />
            <button
              onClick={handleAdd}
              className="bg-cyan-500 text-slate-950 px-4 py-2 rounded-lg text-sm font-medium hover:bg-cyan-400 transition-colors"
            >
              Add
            </button>
          </div>
        </div>
      </div>

      <div className="bg-slate-900 rounded-xl border border-slate-800">
        <div className="p-5 border-b border-slate-800">
          <h3 className="text-sm font-medium text-slate-300">Transaction History</h3>
        </div>
        {history.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No transactions yet</div>
        ) : (
          <div className="divide-y divide-slate-800/50">
            {history.map((tx) => (
              <div key={tx.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="text-sm text-white">{tx.description || tx.type}</p>
                  <p className="text-xs text-slate-500">
                    {new Date(tx.created_at).toLocaleString()}
                  </p>
                </div>
                <span className={`font-mono font-bold text-sm ${typeColors[tx.type] || 'text-slate-400'}`}>
                  {tx.amount > 0 ? '+' : ''}{tx.amount}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
