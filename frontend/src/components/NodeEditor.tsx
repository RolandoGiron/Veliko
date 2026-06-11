import { useState } from "react";
import type { NodeOut, NodeType, ValidationOut } from "../api/types";
import { FreshnessBadge } from "./FreshnessBadge";
import { ValidationPanel } from "./ValidationPanel";
import { NODE_META } from "../ui/nodeMeta";

interface Props {
  node: NodeOut;
  type: NodeType;
  index: number;
  last: boolean;
  onSave: (content: string) => Promise<void>;
  onValidate: () => Promise<ValidationOut>;
}

export function NodeEditor({ node, type, index, last, onSave, onValidate }: Props) {
  const [content, setContent] = useState(node.content);
  const [result, setResult] = useState<ValidationOut | null>(null);
  const [busy, setBusy] = useState(false);
  const meta = NODE_META[type];

  return (
    <section
      className="node rise"
      data-state={node.state}
      style={{ "--d": `${120 + index * 90}ms` } as React.CSSProperties}
    >
      <div className="node__rail" aria-hidden>
        <span className="node__marker">{meta.roman}</span>
        {!last && <span className="node__line" />}
      </div>

      <div className="card node__card">
        <header className="node__head">
          <div>
            <h3 className="node__title">{meta.label}</h3>
            <p className="node__hint">{meta.hint}</p>
          </div>
          <FreshnessBadge state={node.state} />
        </header>

        <textarea
          className="field"
          rows={5}
          placeholder={`Escribe aquí tu ${meta.label.toLowerCase()}…`}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onBlur={() => onSave(content)}
        />

        <div className="node__actions">
          <button
            className={`btn btn--primary ${busy ? "is-busy" : ""}`}
            disabled={busy || !content.trim()}
            onClick={async () => {
              setBusy(true);
              await onSave(content);
              try {
                setResult(await onValidate());
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy ? "Validando coherencia…" : "Validar coherencia"}
          </button>
        </div>

        <ValidationPanel result={result} />
      </div>
    </section>
  );
}
