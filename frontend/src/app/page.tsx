"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Filter,
  GitPullRequest,
  Search,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { fetchReviews, fetchStats, DashboardStats, ReviewSummary } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { VerdictBadge } from "@/components/VerdictBadge";
import { EmptyState } from "@/components/EmptyState";
import { TableSkeleton } from "@/components/LoadingSkeleton";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [reviews, setReviews] = useState<ReviewSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [verdictFilter, setVerdictFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    Promise.all([fetchStats(), fetchReviews()]).then(([s, r]) => {
      setStats(s);
      setReviews(r);
      setLoading(false);
    });
  }, []);

  const filteredReviews = reviews.filter((r) => {
    const matchesVerdict = verdictFilter === "ALL" || r.verdict === verdictFilter;
    const matchesSearch =
      r.pr_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (r.repo_full_name && r.repo_full_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      r.pr_author.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesVerdict && matchesSearch;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-white tracking-tight">Review Activity</h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20">
              Live Feed
            </span>
          </div>
          <p className="text-sm text-gray-400">
            Real-time PR reviews, blocker prevention metrics, and security insights.
          </p>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <div className="p-5 rounded-xl border border-border bg-surface relative overflow-hidden transition-all hover:border-purple-500/40">
          <div className="flex items-center justify-between text-gray-400 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">PRs Reviewed</span>
            <GitPullRequest className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-3xl font-black text-white tracking-tight">
            {stats ? stats.total_reviews : 0}
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Across {stats ? stats.active_repositories_count : 0} active repos
          </p>
        </div>

        <div className="p-5 rounded-xl border border-red-500/30 bg-surface relative overflow-hidden transition-all hover:border-red-500/60">
          <div className="flex items-center justify-between text-gray-400 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-red-400">
              Blockers Prevented
            </span>
            <ShieldAlert className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-3xl font-black text-red-400 tracking-tight">
            {stats ? stats.total_blocking_prevented : 0}
          </div>
          <p className="text-xs text-gray-500 mt-1">Bugs & vulnerabilities intercepted</p>
        </div>

        <div className="p-5 rounded-xl border border-amber-500/30 bg-surface relative overflow-hidden transition-all hover:border-amber-500/60">
          <div className="flex items-center justify-between text-gray-400 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">
              Suggestions Made
            </span>
            <Sparkles className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-black text-amber-400 tracking-tight">
            {stats ? stats.total_suggestions_made : 0}
          </div>
          <p className="text-xs text-gray-500 mt-1">Architecture & perf enhancements</p>
        </div>

        <div className="p-5 rounded-xl border border-blue-500/30 bg-surface relative overflow-hidden transition-all hover:border-blue-500/60">
          <div className="flex items-center justify-between text-gray-400 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-blue-400">
              Avg Analysis Time
            </span>
            <Clock className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-3xl font-black text-white tracking-tight">
            {stats && stats.avg_duration_ms > 0
              ? `${(stats.avg_duration_ms / 1000).toFixed(1)}s`
              : "0.0s"}
          </div>
          <p className="text-xs text-gray-500 mt-1">From webhook to posted review</p>
        </div>
      </div>

      {/* Reviews Section */}
      <div className="rounded-xl border border-border bg-surface overflow-hidden shadow-2xl">
        {/* Filter bar */}
        <div className="p-4 border-b border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface-raised/30">
          <div className="flex items-center gap-1 bg-surface p-1 rounded-lg border border-border">
            {["ALL", "REQUEST_CHANGES", "APPROVE", "COMMENT"].map((v) => (
              <button
                key={v}
                onClick={() => setVerdictFilter(v)}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                  verdictFilter === v
                    ? "bg-purple-600 text-white shadow"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                {v === "ALL" ? "All Reviews" : v === "REQUEST_CHANGES" ? "Changes Requested" : v === "APPROVE" ? "Approved" : "Commented"}
              </button>
            ))}
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Filter by PR, repo, author..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-surface border border-border text-xs rounded-lg pl-9 pr-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
            />
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <TableSkeleton />
        ) : filteredReviews.length === 0 ? (
          <EmptyState type="reviews" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border/60 bg-surface-raised/60 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  <th className="px-6 py-3.5">Repository & PR</th>
                  <th className="px-6 py-3.5">Verdict</th>
                  <th className="px-6 py-3.5">Findings Breakdown</th>
                  <th className="px-6 py-3.5">Author</th>
                  <th className="px-6 py-3.5">Duration</th>
                  <th className="px-6 py-3.5">Date</th>
                  <th className="px-6 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60 text-sm">
                {filteredReviews.map((rev) => (
                  <tr
                    key={rev.id}
                    className="hover:bg-surface-raised/40 transition-colors group"
                  >
                    <td className="px-6 py-4">
                      <div className="font-semibold text-white flex items-center gap-2 group-hover:text-purple-300 transition-colors">
                        <span>{rev.pr_title}</span>
                        <span className="text-xs font-mono text-purple-400 font-bold">
                          #{rev.pr_number}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400 font-mono mt-0.5 flex items-center gap-2">
                        <span>{rev.repo_full_name || "Unknown Repo"}</span>
                        <span>&bull;</span>
                        <span className="text-gray-500">{rev.head_sha.slice(0, 7)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <VerdictBadge verdict={rev.verdict} size="sm" />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5 text-xs">
                        {rev.metrics.blocking_count > 0 && (
                          <span className="px-2 py-0.5 rounded bg-red-500/15 text-red-400 font-semibold border border-red-500/20">
                            {rev.metrics.blocking_count} blocking
                          </span>
                        )}
                        {rev.metrics.suggestion_count > 0 && (
                          <span className="px-2 py-0.5 rounded bg-amber-500/15 text-amber-400 font-semibold border border-amber-500/20">
                            {rev.metrics.suggestion_count} suggestions
                          </span>
                        )}
                        {rev.metrics.nitpick_count > 0 && (
                          <span className="px-2 py-0.5 rounded bg-blue-500/15 text-blue-400 font-semibold border border-blue-500/20">
                            {rev.metrics.nitpick_count} nitpicks
                          </span>
                        )}
                        {rev.metrics.total_findings === 0 && (
                          <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 font-semibold border border-emerald-500/20">
                            0 issues
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-300 font-mono text-xs">@{rev.pr_author}</td>
                    <td className="px-6 py-4 text-xs font-mono text-gray-400">
                      {(rev.metrics.processing_duration_ms / 1000).toFixed(1)}s
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-400">
                      {formatDate(rev.created_at)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        href={`/reviews/${rev.id}`}
                        className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold bg-surface-raised hover:bg-purple-600 hover:text-white text-gray-200 border border-border transition-all shadow-sm"
                      >
                        Inspect &rarr;
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
