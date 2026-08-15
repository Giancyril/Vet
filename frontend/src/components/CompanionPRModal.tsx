"use client";

import { useState } from "react";
import { Check, ExternalLink, GitPullRequest, Loader2, Sparkles, X } from "lucide-react";

interface CompanionPRModalProps {
  reviewId: string;
  prNumber: number;
  fixableCount: number;
}

interface PlanData {
  review_id: string;
  branch_name: string;
  total_fixes: int;
  patches: Array<{
    file_path: string;
    diff: string;
    findings_fixed: string[];
  }>;
}

export function CompanionPRModal({ reviewId, prNumber, fixableCount }: CompanionPRModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [createdResult, setCreatedResult] = useState<{
    pr_number?: number;
    pr_url?: string;
    message: string;
  } | null>(null);

  const fetchPlan = async () => {
    setIsLoading(true);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiBase}/api/v1/reviews/${reviewId}/remediation-plan`);
      if (res.ok) {
        const data = await res.json();
        setPlan(data);
      }
    } catch (e) {
      console.error("Failed to load remediation plan", e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpen = () => {
    setIsOpen(true);
    fetchPlan();
  };

  const handleCreatePR = async () => {
    setIsCreating(true);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiBase}/api/v1/reviews/${reviewId}/create-companion-pr`, {
        method: "POST",
      });
      const data = await res.json();
      setCreatedResult(data);
    } catch (e) {
      setCreatedResult({
        message: "Failed to connect to backend server.",
      });
    } finally {
      setIsCreating(false);
    }
  };

  if (fixableCount === 0) return null;

  return (
    <>
      <button
        onClick={handleOpen}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-purple-500/20 transition-all hover:scale-105 active:scale-95"
      >
        <Sparkles className="w-3.5 h-3.5 text-yellow-300 animate-pulse" />
        Auto-Remediate ({fixableCount} Fixes)
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-surface border border-border rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-6 border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center">
                  <GitPullRequest className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Auto-Remediation Companion PR</h3>
                  <p className="text-xs text-gray-400">Generate automated PR with fixes for #{prNumber}</p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-surface-raised transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-4 flex-1">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                  <Loader2 className="w-8 h-8 animate-spin text-purple-400 mb-3" />
                  <p className="text-sm">Calculating patch diffs across files...</p>
                </div>
              ) : createdResult ? (
                <div className="p-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-center space-y-4">
                  <div className="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
                    <Check className="w-6 h-6" />
                  </div>
                  <h4 className="text-base font-bold text-white">{createdResult.message}</h4>
                  {createdResult.pr_url && (
                    <a
                      href={createdResult.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-500 text-black font-semibold text-sm hover:bg-emerald-400 transition-colors shadow-lg"
                    >
                      View Companion PR #{createdResult.pr_number}
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>
              ) : plan ? (
                <>
                  <div className="p-4 rounded-lg bg-surface-raised border border-border text-xs text-gray-300 space-y-1">
                    <p>
                      Target Branch: <span className="font-mono text-purple-400 font-bold">{plan.branch_name}</span>
                    </p>
                    <p>Total Actionable Fixes: <span className="font-bold text-emerald-400">{plan.total_fixes}</span></p>
                  </div>

                  {plan.patches.map((patch, idx) => (
                    <div key={idx} className="rounded-xl border border-border overflow-hidden bg-background">
                      <div className="p-3 bg-surface-raised border-b border-border text-xs font-mono text-gray-300 flex items-center justify-between">
                        <span>{patch.file_path}</span>
                        <span className="text-[11px] text-purple-400 font-sans">
                          {patch.findings_fixed.length} fix(es)
                        </span>
                      </div>
                      <pre className="p-3 text-[11px] font-mono text-gray-300 overflow-x-auto max-h-48 leading-relaxed">
                        <code>{patch.diff || "No diff content generated"}</code>
                      </pre>
                    </div>
                  ))}
                </>
              ) : null}
            </div>

            {/* Modal Footer */}
            {!createdResult && (
              <div className="p-4 border-t border-border bg-surface-raised flex items-center justify-end gap-3">
                <button
                  onClick={() => setIsOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreatePR}
                  disabled={isCreating || isLoading || !plan || plan.total_fixes === 0}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-semibold shadow-lg shadow-purple-500/20 transition-all"
                >
                  {isCreating && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {isCreating ? "Pushing Branch & Opening PR..." : "Create Companion PR on GitHub"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
