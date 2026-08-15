import { AlertCircle, Check, Copy, FileCode2, Sparkles, AlertTriangle, Info } from "lucide-react";
import { useState } from "react";
import { Finding } from "@/lib/api";
import { cn } from "@/lib/utils";

interface FindingCardProps {
  finding: Finding;
}

export function FindingCard({ finding }: FindingCardProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (finding.suggested_fix) {
      navigator.clipboard.writeText(finding.suggested_fix);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case "blocking":
        return {
          badge: "bg-red-500/15 text-red-400 border-red-500/30",
          border: "border-red-500/20",
          icon: <AlertCircle className="w-4 h-4 text-red-400" />,
          label: "Blocking Issue",
        };
      case "suggestion":
        return {
          badge: "bg-amber-500/15 text-amber-400 border-amber-500/30",
          border: "border-amber-500/20",
          icon: <Sparkles className="w-4 h-4 text-amber-400" />,
          label: "Suggestion",
        };
      default:
        return {
          badge: "bg-blue-500/15 text-blue-400 border-blue-500/30",
          border: "border-blue-500/20",
          icon: <Info className="w-4 h-4 text-blue-400" />,
          label: "Nitpick",
        };
    }
  };

  const style = getSeverityStyle(finding.severity);

  return (
    <div className={cn("rounded-xl border bg-surface p-5 transition-all", style.border)}>
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-2.5 flex-wrap">
          <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border", style.badge)}>
            {style.icon}
            {style.label}
          </span>

          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-mono bg-surface-raised text-gray-300 border border-border">
            <FileCode2 className="w-3.5 h-3.5 text-gray-400" />
            {finding.file_path}:{finding.line_number}
          </span>

          <span className="text-xs px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 font-medium capitalize">
            {finding.category.replace("_", " ")}
          </span>
        </div>
      </div>

      <h4 className="text-base font-semibold text-white mb-2">{finding.title}</h4>
      <p className="text-sm text-gray-300 leading-relaxed mb-4">{finding.explanation}</p>

      {finding.suggested_fix && (
        <div className="rounded-lg border border-border bg-background/90 overflow-hidden">
          <div className="flex items-center justify-between px-3 py-1.5 bg-surface-raised border-b border-border text-xs text-gray-400 font-mono">
            <span>Suggested Replacement (Line {finding.line_number})</span>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-gray-300 hover:text-white transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <pre className="p-3 text-xs font-mono text-emerald-300 overflow-x-auto">
            <code>{finding.suggested_fix}</code>
          </pre>
        </div>
      )}
    </div>
  );
}
