"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Check, Info, Save, Settings, Shield, Sparkles } from "lucide-react";
import { fetchRepositories, updateRepoConfig, Repository, RepoConfigData } from "@/lib/api";
import { cn } from "@/lib/utils";
import { PolicyEngineManager } from "@/components/PolicyEngineManager";

const CATEGORIES = [
  { id: "security", label: "Security & Vulnerabilities", desc: "Hardcoded secrets, SQL injection, XSS, unsafe inputs" },
  { id: "logic_bug", label: "Logic & Correctness", desc: "Edge cases, unhandled errors, state mutations, async leaks" },
  { id: "performance", label: "Performance & Scaling", desc: "N+1 queries, memory bottlenecks, expensive loops" },
  { id: "error_handling", label: "Error Handling", desc: "Missing catch blocks, unvalidated assumptions" },
  { id: "style", label: "Style & Readability", desc: "Naming conventions, complexity, code organization" },
  { id: "test_coverage", label: "Test Coverage", desc: "Missing test assertions, untested edge cases" },
];

function ConfigContent() {
  const searchParams = useSearchParams();
  const repoParam = searchParams.get("repo");

  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>("");
  const [minSeverity, setMinSeverity] = useState<"blocking" | "suggestion" | "nitpick">("suggestion");
  const [autoRequestChanges, setAutoRequestChanges] = useState(true);
  const [enabledCategories, setEnabledCategories] = useState<string[]>([
    "security",
    "logic_bug",
    "performance",
    "error_handling",
    "style",
    "test_coverage",
  ]);
  const [maxComments, setMaxComments] = useState(15);
  const [customInstructions, setCustomInstructions] = useState("");
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchRepositories().then((data) => {
      setRepos(data);
      if (data.length > 0) {
        const target = repoParam ? data.find((r) => r.id === repoParam) || data[0] : data[0];
        setSelectedRepoId(target.id);
        loadRepoConfig(target);
      }
    });
  }, [repoParam]);

  const loadRepoConfig = (repo: Repository) => {
    if (repo.config) {
      setMinSeverity(repo.config.min_severity as any || "suggestion");
      setAutoRequestChanges(repo.config.auto_request_changes ?? true);
      setEnabledCategories(repo.config.enabled_categories || []);
      setMaxComments(repo.config.max_comments_per_pr || 15);
      setCustomInstructions(repo.config.custom_instructions || "");
    }
  };

  const handleRepoChange = (id: string) => {
    setSelectedRepoId(id);
    const repo = repos.find((r) => r.id === id);
    if (repo) loadRepoConfig(repo);
  };

  const toggleCategory = (catId: string) => {
    setEnabledCategories((prev) =>
      prev.includes(catId) ? prev.filter((c) => c !== catId) : [...prev, catId]
    );
  };

  const handleSave = async () => {
    if (!selectedRepoId) return;
    setSaving(true);

    const payload: Partial<RepoConfigData> = {
      min_severity: minSeverity,
      auto_request_changes: autoRequestChanges,
      enabled_categories: enabledCategories,
      max_comments_per_pr: maxComments,
      custom_instructions: customInstructions,
    };

    const updated = await updateRepoConfig(selectedRepoId, payload);
    setSaving(false);
    if (updated) {
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-16">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Reviewer Settings</h1>
          <p className="text-sm text-gray-400 mt-1">
            Fine-tune Gemini AI severity thresholds, category filters, and custom instructions.
          </p>
        </div>

        {repos.length > 0 && (
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 font-medium">Repository:</label>
            <select
              value={selectedRepoId}
              onChange={(e) => handleRepoChange(e.target.value)}
              className="bg-surface-raised border border-border text-white text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-purple-500"
            >
              {repos.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.full_name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {repos.length === 0 ? (
        <div className="p-12 text-center rounded-xl border border-border bg-surface text-gray-400 text-sm">
          No repositories available to configure. Install your GitHub App first.
        </div>
      ) : (
        <div className="space-y-6">
          {/* Minimum Severity Card */}
          <div className="rounded-xl border border-border bg-surface p-6">
            <h3 className="text-base font-semibold text-white mb-1">Minimum Severity Threshold</h3>
            <p className="text-xs text-gray-400 mb-4">
              Control the noise level. Findings below this severity will not be posted to pull requests.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { id: "blocking", label: "🚨 Blocking Only", desc: "Critical bugs and security holes" },
                { id: "suggestion", label: "💡 Suggestions + Blocking", desc: "Recommended baseline (Default)" },
                { id: "nitpick", label: "🔍 All Findings", desc: "Includes style & minor polish" },
              ].map((lvl) => (
                <button
                  key={lvl.id}
                  onClick={() => setMinSeverity(lvl.id as any)}
                  className={cn(
                    "p-4 rounded-xl border text-left transition-all",
                    minSeverity === lvl.id
                      ? "border-purple-500 bg-purple-500/10 text-white"
                      : "border-border bg-surface-raised/40 text-gray-400 hover:border-gray-600"
                  )}
                >
                  <div className="text-sm font-semibold text-white mb-1">{lvl.label}</div>
                  <div className="text-xs text-gray-400">{lvl.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Auto Request Changes Card */}
          <div className="rounded-xl border border-border bg-surface p-6 flex items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-semibold text-white mb-1">Auto Request Changes</h3>
              <p className="text-xs text-gray-400 max-w-lg">
                Automatically submit GitHub PR review with `REQUEST_CHANGES` verdict whenever blocking bugs or security flaws are discovered.
              </p>
            </div>
            <button
              onClick={() => setAutoRequestChanges(!autoRequestChanges)}
              className={cn(
                "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none",
                autoRequestChanges ? "bg-purple-600" : "bg-surface-raised border-border"
              )}
            >
              <span
                className={cn(
                  "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
                  autoRequestChanges ? "translate-x-5" : "translate-x-0"
                )}
              />
            </button>
          </div>

          {/* Enabled Categories Card */}
          <div className="rounded-xl border border-border bg-surface p-6">
            <h3 className="text-base font-semibold text-white mb-1">Active Review Categories</h3>
            <p className="text-xs text-gray-400 mb-4">
              Select which areas the AI reviewer should inspect on each PR.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {CATEGORIES.map((cat) => {
                const checked = enabledCategories.includes(cat.id);
                return (
                  <div
                    key={cat.id}
                    onClick={() => toggleCategory(cat.id)}
                    className={cn(
                      "p-3.5 rounded-xl border cursor-pointer flex items-start gap-3 transition-all",
                      checked
                        ? "border-purple-500/50 bg-purple-500/5"
                        : "border-border bg-surface-raised/30 opacity-60 hover:opacity-80"
                    )}
                  >
                    <div
                      className={cn(
                        "w-5 h-5 rounded flex items-center justify-center mt-0.5 border text-xs",
                        checked
                          ? "bg-purple-600 border-purple-500 text-white"
                          : "border-border bg-surface-raised"
                      )}
                    >
                      {checked && <Check className="w-3.5 h-3.5" />}
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-white">{cat.label}</div>
                      <div className="text-[11px] text-gray-400 mt-0.5">{cat.desc}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Max Comments Slider */}
          <div className="rounded-xl border border-border bg-surface p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-base font-semibold text-white">Max Inline Comments per PR</h3>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
                {maxComments} comments
              </span>
            </div>
            <p className="text-xs text-gray-400 mb-4">
              Limits the maximum number of inline comments posted to avoid overwhelming developers.
            </p>
            <input
              type="range"
              min="1"
              max="50"
              value={maxComments}
              onChange={(e) => setMaxComments(parseInt(e.target.value))}
              className="w-full h-2 bg-surface-raised rounded-lg appearance-none cursor-pointer accent-purple-500"
            />
          </div>

          {/* Custom Instructions Textarea */}
          <div className="rounded-xl border border-border bg-surface p-6">
            <h3 className="text-base font-semibold text-white mb-1">Custom Review Instructions</h3>
            <p className="text-xs text-gray-400 mb-3">
              Prompt guidelines appended to the AI reviewer (e.g. team coding conventions, preferred libraries, naming rules).
            </p>
            <textarea
              rows={4}
              value={customInstructions}
              onChange={(e) => setCustomInstructions(e.target.value)}
              placeholder="e.g. Always ensure database queries use async transactions. Prefer arrow functions in TypeScript. Flag any missing error boundaries in React."
              className="w-full bg-background border border-border rounded-lg p-3.5 text-xs text-gray-200 focus:outline-none focus:border-purple-500 font-mono"
            />
          </div>

          {/* Policy Engine Rules Section */}
          <div className="pt-2">
            <h2 className="text-lg font-bold text-white mb-2">Repository Policy Engine</h2>
            <p className="text-xs text-gray-400 mb-4">
              Enforce bespoke codebase rules (regex patterns and AST static checks) evaluated on every PR.
            </p>
            {selectedRepoId && <PolicyEngineManager repoId={selectedRepoId} />}
          </div>

          {/* Save Action Bar */}
          <div className="flex items-center justify-end gap-3 pt-4">
            <button
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-500/20 transition-all disabled:opacity-50"
            >
              {saved ? <Check className="w-4 h-4 text-emerald-300" /> : <Save className="w-4 h-4" />}
              {saving ? "Saving..." : saved ? "Settings Saved!" : "Save Configuration"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ConfigPage() {
  return (
    <Suspense fallback={<div className="max-w-4xl mx-auto p-8 text-center text-gray-400">Loading settings...</div>}>
      <ConfigContent />
    </Suspense>
  );
}
