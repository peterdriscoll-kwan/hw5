import { useEffect, useState } from "react";
import type { ApprovePaymentResponse } from "../types";
import type { PaymentPrefill } from "../prefill";

interface Props {
  ticketId: number;
  prefill: PaymentPrefill | null;
  onApprove: (payload: { kind: "invoice" | "lease"; ref_id: number; amount: number; account: string; approved_by: string }) => Promise<void>;
  lastResult: ApprovePaymentResponse | null;
  busy: boolean;
}

export default function ApprovalSlip({ ticketId, prefill, onApprove, lastResult, busy }: Props) {
  const [kind, setKind] = useState<"invoice" | "lease">(prefill?.kind ?? "invoice");
  const [refId, setRefId] = useState(prefill?.ref_id?.toString() ?? "");
  const [amount, setAmount] = useState(prefill?.amount?.toString() ?? "");
  const [account, setAccount] = useState("checking");
  const [approvedBy, setApprovedBy] = useState("");

  useEffect(() => {
    if (prefill) {
      setKind(prefill.kind);
      setRefId(prefill.ref_id.toString());
      setAmount(prefill.amount.toString());
    }
  }, [prefill, ticketId]);

  return (
    <form
      className="approval-slip"
      onSubmit={(e) => {
        e.preventDefault();
        if (!refId || !amount || !approvedBy.trim()) return;
        void onApprove({ kind, ref_id: Number(refId), amount: Number(amount), account, approved_by: approvedBy.trim() });
      }}
    >
      <div className="approval-slip__stamp">Pay to the Order Of</div>
      <div className="approval-slip__grid">
        <label>
          Kind
          <select value={kind} onChange={(e) => setKind(e.target.value as "invoice" | "lease")}>
            <option value="invoice">Vendor invoice</option>
            <option value="lease">Lease / rent</option>
          </select>
        </label>
        <label>
          {kind === "invoice" ? "Invoice #" : "Lease #"}
          <input value={refId} onChange={(e) => setRefId(e.target.value)} placeholder="e.g. 501" inputMode="numeric" />
        </label>
        <label>
          Amount ($)
          <input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="e.g. 840.00" inputMode="decimal" />
        </label>
        <label>
          Account
          <input value={account} onChange={(e) => setAccount(e.target.value)} />
        </label>
        <label className="approval-slip__signature">
          Approved by (human signature)
          <input
            value={approvedBy}
            onChange={(e) => setApprovedBy(e.target.value)}
            placeholder="Your name"
            required
          />
        </label>
      </div>
      <button className="wax-button" type="submit" disabled={busy}>
        {busy ? "Processing…" : "Approve & Pay"}
      </button>
      {lastResult && (
        <p className={`approval-slip__result ${lastResult.paid ? "approval-slip__result--ok" : "approval-slip__result--refused"}`}>
          {lastResult.paid
            ? `Paid $${lastResult.amount?.toFixed(2)} — new balance $${lastResult.new_cash_balance?.toFixed(2)}.`
            : lastResult.message}
        </p>
      )}
    </form>
  );
}
