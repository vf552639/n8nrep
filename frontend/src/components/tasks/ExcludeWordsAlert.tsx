import { AlertTriangle } from "lucide-react";

interface Props {
  violations: Record<string, number> | string[];
}

export default function ExcludeWordsAlert({ violations }: Props) {
  if (!violations || Object.keys(violations).length === 0) return null;

  const renderViolations = () => {
    if (Array.isArray(violations)) {
      return violations.join(", ");
    }
    return Object.entries(violations)
      .map(([word, count]) => `${word} (${count})`)
      .join(", ");
  };

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-md p-3 flex gap-3 text-sm text-amber-800">
      <AlertTriangle className="w-5 h-5 shrink-0 text-amber-600 p-0.5" />
      <div>
        <div className="font-medium text-amber-900 mb-1">Found excluded words in the generation:</div>
        <div className="font-mono text-xs font-semibold">{renderViolations()}</div>
      </div>
    </div>
  );
}
