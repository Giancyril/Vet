import Link from "next/link";
import { AlertCircle, CheckCircle2, Clock, GitPullRequest, ShieldAlert, Sparkles } from "lucide-react";
import { fetchReviews, fetchStats } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { VerdictBadge } from "@/components/VerdictBadge";

export default async function DashboardPage() {
  const [stats, reviews] = await Promise.all([fetchStats(), fetchReviews()]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Review Activity</h1>
          <p className="text-sm text-gray-400 mt-1">
            Real-time PR reviews, blocker prevention metrics, and security insights.
          </p>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <div className="p-5 rounded-xl border border-border bg-surface relative overflow-hidden">
          <div className="flex items-center justify-between text-gray-400 mb-3">
            <span className="text-xs font-medium uppercase tracking-wider">PRs Reviewed</span>
            <GitPullRequest className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white">{stats.total_reviews}</div>
          <p className="text-xs text-gray-500 mt-1">Across {stats.active_repositories_count} active repos</p>
        </div>

        <div className="p-5 rounded-xl border border-red-500/20 bg-surface relative overflow-hidden">
          <div className="flex items-center justify-between text-gray-400 mb-3">
            <span className="text-xs font-medium uppercase tracking-wider text-red-400">Blockers Prevented</span>
            <ShieldAlert className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-2xl font-bold text-red-400">{stats.total_blocking_prevented}</div>
          <p className="text-xs text-gray-500 mt-1">Bugs & security vulnerabilities</p>
        </div>

        <div className="p-5 rounded-xl border border-border bg-surface relative overflow-hidden">
          <div className="flex items-center justify-between text-gray-400 mb-3">
            <span className="text-xs font-medium uppercase tracking-wider text-amber-400">Suggestions Made</span>
            <Sparkles className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">{stats.total_suggestions_made}</div>
          <p className="text-xs text-gray-500 mt-1">Performance & architecture tips</p>
        </div>

        <div className="p-5 rounded-xl border border-border bg-surface relative overflow-hidden">
          <div className="flex items-center justify-between text-gray-400 mb-3">
            <span className="text-xs font-medium uppercase tracking-wider text-blue-400">Avg Analysis Time</span>
            <Clock className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {stats.avg_duration_ms > 0 ? `${(stats.avg_duration_ms / 1000).toFixed(1)}s` : "0.0s"}
          </div>
          <p className="text-xs text-gray-500 mt-1">From webhook to posted review</p>
        </div>
      </div>

      {/* Reviews Table */}
      <div className="rounded-xl border border-border bg-surface overflow-hidden">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Recent Pull Request Reviews</h2>
          <span className="text-xs text-gray-400">{reviews.length} reviews recorded</span>
        </div>

        {reviews.length === 0 ? (
          <div className="py-16 text-center">
            <GitPullRequest className="w-10 h-10 text-gray-600 mx-auto mb-3 animate-pulse" />
            <h3 className="text-base font-medium text-gray-300">No PR reviews yet</h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
              Once you open or update a PR in your connected GitHub repository, the AI review will appear here automatically.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border/60 bg-surface-raised/40 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  <th className="px-6 py-3">Repository & PR</th>
                  <th className="px-6 py-3">Verdict</th>
                  <th className="px-6 py-3">Findings Breakdown</th>
                  <th className="px-6 py-3">Author</th>
                  <th className="px-6 py-3">Duration</th>
                  <th className="px-6 py-3">Date</th>
                  <th className="px-6 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60 text-sm">
                {reviews.map((rev) => (
                  <tr key={rev.id} className="hover:bg-surface-raised/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-semibold text-white flex items-center gap-2">
                        <span>{rev.pr_title}</span>
                        <span className="text-xs font-mono text-purple-400">#{rev.pr_number}</span>
                      </div>
                      <div className="text-xs text-gray-400 font-mono mt-0.5">
                        {rev.repo_full_name || "Unknown Repo"} &bull; {rev.head_sha.slice(0, 7)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <VerdictBadge verdict={rev.verdict} size="sm" />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 text-xs">
                        <span className="px-2 py-0.5 rounded bg-red-500/10 text-red-400 font-medium">
                          {rev.metrics.blocking_count} blocking
                        </span>
                        <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 font-medium">
                          {rev.metrics.suggestion_count} suggestions
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-300">@{rev.pr_author}</td>
                    <td className="px-6 py-4 text-xs font-mono text-gray-400">
                      {(rev.metrics.processing_duration_ms / 1000).toFixed(1)}s
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-400">{formatDate(rev.created_at)}</td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        href={`/reviews/${rev.id}`}
                        className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-raised hover:bg-purple-600 hover:text-white text-gray-300 border border-border transition-all"
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
