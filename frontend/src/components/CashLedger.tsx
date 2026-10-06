import { useEffect, useRef, useState } from "react";

interface Props {
  balance: number | null;
  asOf: string | null;
}

export default function CashLedger({ balance, asOf }: Props) {
  const [flash, setFlash] = useState(false);
  const previous = useRef<number | null>(null);

  useEffect(() => {
    if (previous.current !== null && balance !== null && balance < previous.current) {
      setFlash(true);
      const t = setTimeout(() => setFlash(false), 1600);
      return () => clearTimeout(t);
    }
    previous.current = balance;
  }, [balance]);

  return (
    <div className={`cash-plaque ${flash ? "cash-plaque--drop" : ""}`}>
      <span className="cash-plaque__label">Checking Balance</span>
      <span className="cash-plaque__amount">
        {balance === null ? "—" : `$${balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
      </span>
      {asOf && <span className="cash-plaque__asof">as of {asOf}</span>}
    </div>
  );
}
