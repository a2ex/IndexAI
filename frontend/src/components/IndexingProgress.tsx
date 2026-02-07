interface Props {
  indexed: number;
  total: number;
}

export default function IndexingProgress({ indexed, total }: Props) {
  const pct = total > 0 ? Math.round((indexed / total) * 100) : 0;

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-gray-200 rounded-full h-3 overflow-hidden">
        <div
          className="h-full bg-green-500 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-sm font-medium text-gray-700 min-w-[48px] text-right">{pct}%</span>
    </div>
  );
}
