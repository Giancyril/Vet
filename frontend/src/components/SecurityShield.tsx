"use client";

import { AlertTriangle, CheckCircle2, Lock, ShieldAlert, ShieldCheck } from "lucide-react";
import { Finding } from "@/lib/api";

interface SecurityShieldProps {
  findings: Finding[];
}

export function SecurityShield({ findings }: SecurityShieldProps) {
  const securityFindings = findings.filter(
    (f) =>
      f.category === "security" ||
      f.title.toLowerCase().includes("secret") ||
      f.title.toLowerCase().includes("vulnerability") ||
      f.explanation.includes("OWASP")
  );

  const secretLeaks = securityFindings.filter(
    (f) => f.title.toLowerCase().includes("secret") || f.title.toLowerCase().includes("token")
  );

  const isClean = securityFindings.length === 0;

  return (
    <div className="rounded-xl border border-border bg-surface p-6 shadow-xl relative overflow-hidden">
      {/* Background subtle glow */}
      <div
        className={`absolute top-0 right-0 w-64 h-64 rounded-full blur-3xl -z-0 pointer-events-none opacity-20 ${
          isClean ? "bg-emerald-500" : "bg-red-500"
        }`}
      />

      <div className="flex items-center justify-between mb-4 relative z-10">
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center border ${
              isClean
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : "bg-red-500/10 border-red-500/30 text-red-400"
            }`}
          >
            {isClean ? <ShieldCheck className="w-5 h-5" /> : <ShieldAlert className="w-5 h-5" />}
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Security Shield & Secret Guard</h3>
            <p className="text-xs text-gray-400">Zero-day secret scanner & OWASP Top 10 compliance</p>
          </div>
        </div>

        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold border ${
            isClean
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
              : "bg-red-500/10 text-red-400 border-red-500/30 animate-pulse"
          }`}
        >
          {isClean ? "Passed Clean" : `${securityFindings.length} Threat(s) Flagged`}
        </span>
      </div>

      {isClean ? (
        <div className="p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-xs text-gray-300 flex items-center gap-3 relative z-10">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          <span>
            No hardcoded secrets, API keys, credentials, or OWASP Top 10 vulnerabilities detected in this diff.
          </span>
        </div>
      ) : (
        <div className="space-y-3 relative z-10">
          {secretLeaks.length > 0 && (
            <div className="p-3.5 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-300 flex items-center gap-2 font-medium">
              <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <span>
                CRITICAL: {secretLeaks.length} potential credential/token leak(s) detected! Immediate rotation required.
              </span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            {securityFindings.map((f, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-surface-raised border border-border flex items-start gap-2.5"
              >
                <Lock className="w-3.5 h-3.5 text-red-400 mt-0.5 flex-shrink-0" />
                <div className="overflow-hidden">
                  <p className="font-semibold text-white truncate">{f.title}</p>
                  <p className="text-gray-400 font-mono text-[11px] truncate">{f.file_path}:{f.line_number}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
