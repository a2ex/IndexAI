import { Globe } from 'lucide-react';
import { useState } from 'react';

interface Props {
  domain: string | null | undefined;
  size?: number;
}

export default function Favicon({ domain, size = 20 }: Props) {
  const [failed, setFailed] = useState(false);

  if (!domain || failed) {
    return <Globe size={size} className="text-slate-500 flex-shrink-0" />;
  }

  return (
    <img
      src={`https://icon.horse/icon/${encodeURIComponent(domain)}`}
      alt=""
      width={size}
      height={size}
      className="flex-shrink-0 rounded-sm"
      onError={() => setFailed(true)}
    />
  );
}
