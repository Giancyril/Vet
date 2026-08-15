"use client";

import { useState } from "react";
import {
  AlertCircle,
  Check,
  ChevronDown,
  ChevronUp,
  Copy,
  FileCode2,
  Info,
  Sparkles,
} from "lucide-react";
import { Finding } from "@/lib/api";
import { cn } from "@/lib/utils";

interface FindingCardProps {
  finding: Finding;
  defaultExpanded?: boolean;
}

export function FindingCard({ finding, defaultExpanded = true }: FindingCardProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(defaultExpanded);

  const handleCopy = () => {
    if (finding.suggested_fix) {
      navigator.clipboard.writeText(finding.suggested_fix);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getSeverityConfig = (severity: string) => {
    switch (severity) {
      case "blocking":
        return {
          pill: "bg-red-500/10 text-red-400 border-red-500/30",
          cardBorder: "border-red-500/30 hover:border-red-500/50",
          bgAccent: "bg-red-500/5",
          icon: <AlertCircle className="w-3.5 h-3.5 text-red-400" />,
          label: "Blocking Issue",
        };
      case "suggestion":
        return {
          pill: "bg-amber-500/10 text-amber-400 border-amber-500/30",
          cardBorder: "border-amber-500/30 hover:border-amber-500/50",
          bgAccent: "bg-amber-500/5",
          icon: <Sparkles className="w-3.5 h-3.5 text-amber-400" />,
          label: "Suggestion",
        };
      default:
        return {
          pill: "bg-blue-500/10 text-blue-400 border-blue-500/30",
          cardBorder: "border-blue-500/30 hover:border-blue-500/50",
          bgAccent: "bg-blue-500/5",
          icon: <Info className="w-3.5 h-3.5 text-blue-400" />,
          label: "Nitpick",
        };
    }
  };

  const config = getSeverityConfig(finding.severity);

  return (
    <div
      className={cn(
        "rounded-xl border bg-surface transition-all duration-200 overflow-hidden",
        config.cardBorder
      )}
    >
      {/* Header bar */}
      <div
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "p-4 flex items-center justify-between cursor-pointer select-none transition-colors",
          config.bgAccent,
          "hover:bg-surface-raised/60"
        )}
      >
        <div className="flex items-center gap-3 flex-wrap">
          <span
            className={cn(
              "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border",
              config.pill
            )}
          >
            {config.icon}
            {config.label}
          </span>

          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono bg-surface-raised text-gray-200 border border-border">
            <FileCode2 className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-gray-400">{finding.file_path}:</span>
            <span className="text-white font-bold">{finding.line_number}</span>
          </span>

          <span className="text-xs px-2.5 py-0.5 rounded-full bg-surface text-gray-400 border border-border font-medium capitalize">
            {finding.category.replace("_", " ")}
          </span>

          <h4 className="text-sm font-semibold text-white ml-1">{finding.title}</h4>
        </div>

        <button className="text-gray-400 hover:text-white p-1">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Expanded body */}
      {expanded && (
        <div className="p-5 border-t border-border/60 space-y-4">
          <div>
            <h5 className="text-[11px] uppercase font-semibold text-gray-400 tracking-wider mb-1.5">
              Explanation & Impact
            </h5>
            <p className="text-sm text-gray-300 leading-relaxed bg-surface-raised/40 p-3.5 rounded-lg border border-border/80">
              {finding.explanation}
            </p>
          </div>

          {finding.suggested_fix && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <h5 className="text-[11px] uppercase font-semibold text-emerald-400 tracking-wider flex items-center gap-1.5">
                  <Check className="w-3.5 h-3.5" /> Suggested Code Fix (Line {finding.line_number})
                </h5>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 text-xs font-medium text-gray-400 hover:text-white transition-colors"
                >
                  {copied ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                  {copied ? "Copied to Clipboard" : "Copy Fix"}
                </button>
              </div>

              <div className="rounded-lg border border-emerald-500/20 bg-background overflow-hidden">
                <div className="px-3 py-1 bg-surface-raised/80 border-b border-border text-[11px] font-mono text-gray-400 flex items-center justify-between">
                  <span>Target: {finding.file_path}</span>
                  <span className="text-emerald-400 font-bold">1-Click Replacement</span>
                </div>
                <pre className="p-3.5 text-xs font-mono text-emerald-300 overflow-x-auto leading-relaxed">
                  <code>{finding.suggested_fix}</code>
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
