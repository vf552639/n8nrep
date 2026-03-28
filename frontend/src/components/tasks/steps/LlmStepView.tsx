import { useMemo, useState } from "react";
import { Copy } from "lucide-react";
import toast from "react-hot-toast";

type TabId = "result" | "prompts" | "variables";

function wordCountLineClass(lossPct: number): string {
  if (lossPct <= 7) return "text-emerald-700";
  if (lossPct <= 15) return "text-amber-600";
  return "text-red-600";
}

function WordCountStats({
  input_word_count,
  output_word_count,
  word_count_warning,
  word_loss_percentage,
}: {
  input_word_count?: number;
  output_word_count?: number;
  word_count_warning?: boolean;
  word_loss_percentage?: number;
}) {
  const hasIn = typeof input_word_count === "number";
  const hasOut = typeof output_word_count === "number";
  if (!hasIn && !hasOut) return null;

  let line = "";
  let lossPct = 0;
  if (hasIn && hasOut && input_word_count > 0) {
    const rel = ((output_word_count - input_word_count) / input_word_count) * 100;
    line = `📊 Words: ${input_word_count} → ${output_word_count} (${rel >= 0 ? "+" : ""}${rel.toFixed(1)}%)`;
    lossPct = ((input_word_count - output_word_count) / input_word_count) * 100;
  } else if (hasOut) {
    line = `📊 Content words: ${output_word_count}`;
  } else {
    return null;
  }

  const displayLossPct =
    typeof word_loss_percentage === "number"
      ? word_loss_percentage
      : hasIn && hasOut && input_word_count > 0
        ? ((input_word_count - output_word_count) / input_word_count) * 100
        : 0;

  return (
    <div className="space-y-2">
      {word_count_warning && hasIn && hasOut && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          ⚠️ Content loss detected: {input_word_count} → {output_word_count} words (−{displayLossPct.toFixed(1)}%). Max
          allowed: 7%
        </div>
      )}
      <p className={`text-sm font-medium ${hasIn && hasOut ? wordCountLineClass(lossPct) : "text-slate-600"}`}>{line}</p>
    </div>
  );
}

function isEmptyVarValue(v: string): boolean {
  const s = String(v ?? "").trim();
  if (!s) return true;
  if (s === "[]" || s === "{}" || s === '""' || s === "None" || s === "null") return true;
  return false;
}

function formatResult(raw: unknown, stepName: string): { mode: "json" | "html" | "text"; body: string } {
  if (raw == null) return { mode: "text", body: "" };
  let text = typeof raw === "string" ? raw : JSON.stringify(raw);
  if (text.length > 50000) text = text.slice(0, 50000) + "\n… [truncated]";

  const t = text.trim();
  if (t.startsWith("<") || (t.includes("<html") && t.includes(">"))) {
    return { mode: "html", body: text };
  }
  if ((t.startsWith("{") || t.startsWith("[")) && (stepName.includes("structure") || stepName.includes("meta") || stepName.includes("fact"))) {
    try {
      const parsed = JSON.parse(text);
      return { mode: "json", body: JSON.stringify(parsed, null, 2) };
    } catch {
      /* fallthrough */
    }
  }
  if (t.startsWith("{") || t.startsWith("[")) {
    try {
      const parsed = JSON.parse(text);
      return { mode: "json", body: JSON.stringify(parsed, null, 2) };
    } catch {
      return { mode: "text", body: text };
    }
  }
  return { mode: "text", body: text };
}

export default function LlmStepView({
  step,
  stepName,
}: {
  step: {
    result?: unknown;
    resolved_prompts?: { system_prompt?: string; user_prompt?: string } | null;
    variables_snapshot?: Record<string, string> | null;
    input_word_count?: number;
    output_word_count?: number;
    word_count_warning?: boolean;
    word_loss_percentage?: number;
  };
  stepName: string;
}) {
  const [tab, setTab] = useState<TabId>("result");

  const formatted = useMemo(() => formatResult(step.result, stepName), [step.result, stepName]);

  const copy = (label: string, text: string) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied`);
  };

  const vars = step.variables_snapshot && typeof step.variables_snapshot === "object" ? step.variables_snapshot : null;
  const rp = step.resolved_prompts;

  return (
    <div className="space-y-3">
      <WordCountStats
        input_word_count={step.input_word_count}
        output_word_count={step.output_word_count}
        word_count_warning={step.word_count_warning}
        word_loss_percentage={step.word_loss_percentage}
      />
      <div className="flex flex-wrap gap-1 border-b border-slate-200 pb-px">
        {(
          [
            ["result", "Result"],
            ["prompts", "Prompts"],
            ["variables", "Variables"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`rounded-t-md px-3 py-1.5 text-xs font-semibold transition-colors ${
              tab === id ? "bg-white text-blue-700 border border-b-0 border-slate-200 -mb-px" : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "result" && (
        <div>
          <div className="mb-2 flex justify-end">
            <button
              type="button"
              onClick={() => copy("Result", formatted.body)}
              className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              <Copy className="h-3.5 w-3.5" /> Copy
            </button>
          </div>
          <pre
            className={`max-h-[min(480px,50vh)] overflow-auto rounded-lg border border-slate-200 p-3 text-xs font-mono ${
              formatted.mode === "html" ? "bg-slate-900 text-emerald-100" : "bg-slate-50 text-slate-800"
            }`}
          >
            {formatted.body || "—"}
          </pre>
        </div>
      )}

      {tab === "prompts" && (
        <div className="space-y-4">
          {!rp ? (
            <p className="text-sm text-slate-500 italic">Промпты не сохранены для этого шага.</p>
          ) : (
            <>
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wide text-slate-600">System prompt</span>
                  <button
                    type="button"
                    onClick={() => copy("System", rp.system_prompt || "")}
                    className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                  >
                    <Copy className="h-3 w-3" /> Copy
                  </button>
                </div>
                <pre className="max-h-48 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-800 whitespace-pre-wrap">
                  {rp.system_prompt || "—"}
                </pre>
              </div>
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wide text-slate-600">User prompt</span>
                  <button
                    type="button"
                    onClick={() => copy("User", rp.user_prompt || "")}
                    className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                  >
                    <Copy className="h-3 w-3" /> Copy
                  </button>
                </div>
                <pre className="max-h-48 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-800 whitespace-pre-wrap">
                  {rp.user_prompt || "—"}
                </pre>
              </div>
            </>
          )}
        </div>
      )}

      {tab === "variables" && (
        <div>
          {!vars || Object.keys(vars).length === 0 ? (
            <p className="text-sm text-slate-500 italic">Снимок переменных недоступен для этого шага.</p>
          ) : (
            <div className="max-h-[min(400px,45vh)] overflow-auto rounded-lg border border-slate-200">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-slate-100">
                  <tr>
                    <th className="px-3 py-2 text-left font-semibold text-slate-700">Variable</th>
                    <th className="px-3 py-2 text-left font-semibold text-slate-700">Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {Object.entries(vars).map(([k, v]) => {
                    const empty = isEmptyVarValue(v);
                    return (
                      <tr key={k} className={empty ? "bg-amber-50" : "bg-emerald-50/60"}>
                        <td className="px-3 py-1.5 font-mono font-medium text-slate-800">{`{{${k}}}`}</td>
                        <td className="px-3 py-1.5 font-mono text-slate-700 break-all max-w-md">{String(v)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
