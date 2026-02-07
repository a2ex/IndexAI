import { useEffect, useState } from 'react';
import { getCredits, getCreditHistory, addCredits } from '../api/client';
import type { CreditTransaction } from '../api/client';

const typeColors: Record<string, string> = {
  purchase: 'text-green-600',
  debit: 'text-red-600',
  refund: 'text-blue-600',
  bonus: 'text-purple-600',
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

  if (loading) return <div className="text-gray-400">Loading...</div>;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Credits</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <p className="text-sm text-gray-500">Current Balance</p>
          <p className="text-4xl font-bold text-gray-900 mt-2">{balance}</p>
          <p className="text-xs text-gray-400 mt-1">credits available</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <p className="text-sm text-gray-500 mb-3">Add Credits</p>
          <div className="flex gap-2">
            <input
              type="number"
              min={1}
              value={addAmount}
              onChange={(e) => setAddAmount(parseInt(e.target.value) || 0)}
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleAdd}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              Add
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-5 border-b border-gray-200">
          <h3 className="text-sm font-medium text-gray-700">Transaction History</h3>
        </div>
        {history.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No transactions yet</div>
        ) : (
          <div className="divide-y divide-gray-100">
            {history.map((tx) => (
              <div key={tx.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="text-sm text-gray-900">{tx.description || tx.type}</p>
                  <p className="text-xs text-gray-400">
                    {new Date(tx.created_at).toLocaleString()}
                  </p>
                </div>
                <span className={`font-mono font-bold text-sm ${typeColors[tx.type] || 'text-gray-600'}`}>
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
