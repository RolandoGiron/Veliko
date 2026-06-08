import { useState } from "react";
import type { NodeOut, ValidationOut } from "../api/types";
import { FreshnessBadge } from "./FreshnessBadge";
import { ValidationPanel } from "./ValidationPanel";

interface Props {
  node: NodeOut;
  onSave: (content: string) => Promise<void>;
  onValidate: () => Promise<ValidationOut>;
}

export function NodeEditor({ node, onSave, onValidate }: Props) {
  const [content, setContent] = useState(node.content);
  const [result, setResult] = useState<ValidationOut | null>(null);
  const [busy, setBusy] = useState(false);
  return (
    <section style={{ marginBottom: 24 }}>
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h3 style={{ textTransform: "capitalize" }}>{node.type}</h3>
        <FreshnessBadge state={node.state} />
      </header>
      <textarea rows={5} style={{ width: "100%" }} value={content}
                onChange={(e) => setContent(e.target.value)} onBlur={() => onSave(content)} />
      <button disabled={busy} onClick={async () => {
        setBusy(true); await onSave(content);
        try { setResult(await onValidate()); } finally { setBusy(false); }
      }}>{busy ? "Validando…" : "Validar coherencia"}</button>
      <ValidationPanel result={result} />
    </section>
  );
}
