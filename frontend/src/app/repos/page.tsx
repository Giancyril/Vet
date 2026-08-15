"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { GitBranch, GitPullRequest, Lock, Power, Settings, ShieldCheck } from "lucide-react";
import { fetchRepositories, toggleRepoActive, Repository } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";

export default function RepositoriesPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRepositories().then((data) => {
      setRepos(data);
      setLoading(false);
    });
  }, []);

  const handleToggle = async (repoId: string, currentActive: boolean) => {
    const nextState = !currentActive;
    // Optimistic update
    setRepos((prev) =>
      prev.map((r) => (r.id === repoId ? { ...r, is_active: nextState } : r))
    );
    await toggleRepoActive(repoId, nextState);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Connected Repositories</h1>
          <p className="text-sm text-gray-400 mt-1">
            Manage repositories connected via your GitHub App and configure active reviews.
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-surface overflow-hidden">
        {loading ? (
          <div className="py-16 text-center text-gray-400 text-sm">Loading repositories...</div>
        ) : repos.length === 0 ? (
          <div className="py-16 text-center">
            <GitPullRequest className="w-10 h-10 text-gray-600 mx-auto mb-3" />
            <h3 className="text-base font-medium text-gray-300">No repositories connected</h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
              Install the GitHub App on your account or repository to start automatic code reviews.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {repos.map((repo) => (
              <div
                key={repo.id}
                className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-surface-raised/30 transition-colors"
              >
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-lg bg-surface-raised border border-border flex items-center justify-center shrink-0">
                    <GitPullRequest className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h3 className="text-base font-semibold text-white">{repo.full_name}</h3>
                      {repo.private && (
                        <span className="inline-flex items-center gap-1 text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-surface-raised text-gray-400 border border-border">
                          <Lock className="w-2.5 h-2.5" /> Private
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-400 mt-1 font-mono">
                      <span className="flex items-center gap-1">
                        <GitBranch className="w-3 h-3" /> {repo.default_branch}
                      </span>
                      <span>{repo.total_reviews_count} reviews</span>
                      <span>Connected {formatDate(repo.created_at)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 self-end sm:self-center">
                  <button
                    onClick={() => handleToggle(repo.id, repo.is_active)}
                    className={cn(
                      "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
                      repo.is_active
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20"
                        : "bg-surface-raised text-gray-400 border-border hover:text-white"
                    )}
                  >
                    <Power className="w-3.5 h-3.5" />
                    {repo.is_active ? "Active" : "Paused"}
                  </button>

                  <Link
                    href={`/config?repo=${repo.id}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-raised hover:bg-purple-600 hover:text-white text-gray-200 border border-border transition-all"
                  >
                    <Settings className="w-3.5 h-3.5" />
                    Configure
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
