import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface DataPoint {
  date: string;
  indexed: number;
  submitted: number;
}

interface Props {
  data: DataPoint[];
}

export default function Charts({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-6 text-center text-slate-500">
        No data yet
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
      <h3 className="text-sm font-medium text-slate-300 mb-4">Indexation Progress</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#64748b' }} />
          <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '0.5rem',
              color: '#e2e8f0',
            }}
          />
          <Legend wrapperStyle={{ color: '#94a3b8' }} />
          <Line type="monotone" dataKey="submitted" stroke="#22d3ee" name="Submitted" strokeWidth={2} />
          <Line type="monotone" dataKey="indexed" stroke="#34d399" name="Indexed" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
