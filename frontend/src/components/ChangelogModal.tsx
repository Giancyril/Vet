"use client";
import { useState } from "react";
import { FileText, Copy, CheckCheck, RefreshCw, X, ExternalLink, ChevronDown, ChevronUp } from "lucide-react";

interface ChangelogData {
  review_id: string;
  conventional_commits: string;
  release_notes: string;
  migration_guide: string;
  executive_summary: string;
  version_bump: string;
}

interface ChangelogModalProps {
  reviewId: string;
  prNumber: number;
  onClose: () => void;
}

type Tab = "commits" | "release" | "migration" | "executive";

const VERSION_BADGE_COLORS: Record<string, string> = {
  major: "bg-red-900/50 border-red-700 text-red-300",
  minor: "bg-yellow-900/50 border-yellow-700 text-yellow-300",
  patch: "bg-green-900/50 border-green-700 text-green-300",
};

export function ChangelogModal({ reviewId, prNumber, onClose }: ChangelogModalProps) {
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [changelog, setChangelog] = useState<ChangelogData | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("commits");
  const [copied, setCopied] = useState(false);
  const [syncSuccess, setSyncSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/reviews/${reviewId}/generate-changelog`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to generate changelog");
      const data = await res.json();
      setChangelog(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const syncToGitHub = async () => {
    if (!changelog) return;
    setSyncing(true);
    try {
      const combined = `## 📝 Changelog\n\n${changelog.conventional_commits}\n\n### Release Notes\n${changelog.release_notes}`;
      const res = await fetch(`/api/reviews/${reviewId}/sync-pr-description`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ changelog_text: combined, append: true }),
      });
      if (!res.ok) throw new Error("Sync failed");
      setSyncSuccess(true);
      setTimeout(() => setSyncSuccess(false), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const copyActive = () => {
    const text = activeContent();
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const activeContent = (): string => {
    if (!changelog) return "";
    const map: Record<Tab, string> = {
      commits: changelog.conventional_commits,
      release: changelog.release_notes,
      migration: changelog.migration_guide || "No migration steps required.",
      executive: changelog.executive_summary,
    };
    return map[activeTab];
  };

  const TABS: { id: Tab; label: string }[] = [
    { id: "commits", label: "Conventional Commits" },
    { id: "release", label: "Release Notes" },
    { id: "migration", label: "Migration Guide" },
    { id: "executive", label: "Executive Summary" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-2xl shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <div className="flex items-center gap-2.5">
            <FileText size={18} className="text-indigo-400" />
            <div>
              <div className="text-sm font-bold text-gray-100">PR Changelog & Release Notes</div>
              <div className="text-xs text-gray-500">PR #{prNumber}</div>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {!changelog ? (
            <div className="flex flex-col items-center justify-center py-12 gap-4">
              <FileText size={40} className="text-gray-600" />
              <div className="text-center">
                <p className="text-gray-300 font-medium">Generate your PR changelog</p>
                <p className="text-gray-500 text-sm mt-1">
                  Gemini 2.5 will analyze this PR and produce conventional commits,
                  release notes, migration guides, and an executive summary.
                </p>
              </div>
              {error && <p className="text-red-400 text-sm">{error}</p>}
              <button
                onClick={generate}
                disabled={loading}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-colors"
              >
                {loading ? <RefreshCw size={15} className="animate-spin" /> : <FileText size={15} />}
                {loading ? "Generating..." : "Generate Changelog"}
              </button>
            </div>
          ) : (
            <>
              {/* Version Bump Badge */}
              <div className="flex items-center gap-3">
                <span className={`px-2.5 py-1 text-xs font-bold rounded border ${VERSION_BADGE_COLORS[changelog.version_bump] || VERSION_BADGE_COLORS.patch}`}>
                  {changelog.version_bump.toUpperCase()} BUMP
                </span>
                <button
                  onClick={generate}
                  disabled={loading}
                  className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
                >
                  <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
                  Regenerate
                </button>
              </div>

              {/* Tabs */}
              <div className="flex gap-1 bg-gray-800/60 rounded-lg p-1 border border-gray-700">
                {TABS.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex-1 text-xs py-1.5 px-2 rounded-md transition-all font-medium ${
                      activeTab === tab.id
                        ? "bg-gray-700 text-gray-100"
                        : "text-gray-500 hover:text-gray-300"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Content */}
              <div className="bg-black/40 border border-gray-700 rounded-lg p-4">
                <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono leading-relaxed">
                  {activeContent() || "No content available."}
                </pre>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        {changelog && (
          <div className="flex items-center justify-between px-5 py-4 border-t border-gray-700 bg-gray-800/30">
            <button
              onClick={copyActive}
              className="flex items-center gap-2 text-xs text-gray-400 hover:text-gray-200 transition-colors"
            >
              {copied ? <CheckCheck size={14} className="text-green-400" /> : <Copy size={14} />}
              {copied ? "Copied!" : "Copy active tab"}
            </button>
            <button
              onClick={syncToGitHub}
              disabled={syncing}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                syncSuccess
                  ? "bg-green-700 text-white"
                  : "bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white"
              }`}
            >
              <ExternalLink size={14} />
              {syncing ? "Syncing..." : syncSuccess ? "Synced!" : "Sync to GitHub PR"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
