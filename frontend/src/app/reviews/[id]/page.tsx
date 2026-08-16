import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Clock, FileCode, GitCommit, GitPullRequest, User } from "lucide-react";
import { fetchReviewDetail } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { VerdictBadge } from "@/components/VerdictBadge";
import { FindingCard } from "@/components/FindingCard";
import { PRChatBot } from "@/components/PRChatBot";
import { ReviewToolbar } from "@/components/ReviewToolbar";
import { SecurityShield } from "@/components/SecurityShield";
import { BlastRadiusGraph } from "@/components/BlastRadiusGraph";
import { LiveAgentStream } from "@/components/LiveAgentStream";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function ReviewDetailPage({ params }: PageProps) {
  const { id } = await params;
  const review = await fetchReviewDetail(id);

  if (!review) {
    notFound();
  }

  const blockingFindings = review.findings.filter((f) => f.severity === "blocking");
  const suggestionFindings = review.findings.filter((f) => f.severity === "suggestion");
  const nitpickFindings = review.findings.filter((f) => f.severity === "nitpick");
  const fixableCount = review.findings.filter((f) => Boolean(f.suggested_fix)).length;

  // Synthesize blast radius data from findings
  const modifiedFiles = Array.from(new Set(review.findings.map((f) => f.file_path).filter(Boolean)));
  const breakingFindings = review.findings.filter((f) => Boolean(f.is_breaking_change || f.title.toLowerCase().includes('breaking')));
  const blastRadiusData = {
    review_id: review.id,
    modified_files: modifiedFiles,
    downstream_files: modifiedFiles.map((f) => `[importers] ${f}`),
    impact_index: Math.min(modifiedFiles.length * 15 + breakingFindings.length * 20, 100),
    impact_level: breakingFindings.length > 0 ? "High" : modifiedFiles.length > 4 ? "Medium" : "Low",
    affected_endpoints: review.findings
      .filter((f) => f.title.toLowerCase().includes("endpoint") || f.title.toLowerCase().includes("route"))
      .map((f) => f.title),
    breaking_exports: breakingFindings.map((f) => `${f.file_path}::${f.title}`),
    summary: `${modifiedFiles.length} file(s) modified, ${breakingFindings.length} breaking change(s) flagged.`,
    dependency_graph: {},
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-16">
      {/* Back button & Action toolbar */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Reviews
        </Link>

        <ReviewToolbar
          reviewId={review.id}
          prNumber={review.pr_number}
          fixableCount={fixableCount}
        />
      </div>

      {/* Header card */}
      <div className="rounded-xl border border-border bg-surface p-6 mb-8 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-border">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-white">{review.pr_title}</h1>
              <span className="text-sm font-mono text-purple-400 font-bold">#{review.pr_number}</span>
            </div>
            <div className="flex items-center gap-4 text-xs text-gray-400 mt-2 flex-wrap font-mono">
              <span className="flex items-center gap-1">
                <GitPullRequest className="w-3.5 h-3.5 text-purple-400" />
                {review.repo_full_name}
              </span>
              <span className="flex items-center gap-1">
                <User className="w-3.5 h-3.5" />
                @{review.pr_author}
              </span>
              <span className="flex items-center gap-1">
                <GitCommit className="w-3.5 h-3.5" />
                {review.head_sha.slice(0, 7)}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                {(review.metrics.processing_duration_ms / 1000).toFixed(1)}s
              </span>
              <span>{formatDate(review.created_at)}</span>
            </div>
          </div>
          <div>
            <VerdictBadge verdict={review.verdict} />
          </div>
        </div>

        {/* Executive summary */}
        <div className="pt-6">
          <h3 className="text-xs uppercase font-medium text-gray-400 tracking-wider mb-2">
            AI Executive Summary & Health Report
          </h3>
          <div className="text-sm text-gray-200 leading-relaxed bg-surface-raised p-4 rounded-lg border border-border whitespace-pre-wrap">
            {review.summary_markdown}
          </div>
        </div>
      </div>

      {/* Live Agent Stream Activity */}
      <div className="mb-8">
        <LiveAgentStream reviewId={review.id} />
      </div>

      {/* Blast Radius Section */}
      <div className="mb-8">
        <BlastRadiusGraph data={blastRadiusData} />
      </div>

      {/* Security Shield Section */}
      <div className="mb-8">
        <SecurityShield findings={review.findings} />
      </div>

      {/* Findings section */}
      <div className="space-y-8">
        {/* Blocking */}
        {blockingFindings.length > 0 && (
          <div>
            <h2 className="text-base font-bold text-red-400 mb-4 flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
              Blocking Issues ({blockingFindings.length})
            </h2>
            <div className="space-y-4">
              {blockingFindings.map((f) => (
                <FindingCard key={f.id} finding={f} />
              ))}
            </div>
          </div>
        )}

        {/* Suggestions */}
        {suggestionFindings.length > 0 && (
          <div>
            <h2 className="text-base font-bold text-amber-400 mb-4 flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
              Suggestions & Improvements ({suggestionFindings.length})
            </h2>
            <div className="space-y-4">
              {suggestionFindings.map((f) => (
                <FindingCard key={f.id} finding={f} />
              ))}
            </div>
          </div>
        )}

        {/* Nitpicks */}
        {nitpickFindings.length > 0 && (
          <div>
            <h2 className="text-base font-bold text-blue-400 mb-4 flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
              Nitpicks & Polish ({nitpickFindings.length})
            </h2>
            <div className="space-y-4">
              {nitpickFindings.map((f) => (
                <FindingCard key={f.id} finding={f} />
              ))}
            </div>
          </div>
        )}

        {review.findings.length === 0 && (
          <div className="p-8 rounded-xl border border-emerald-500/20 bg-emerald-500/5 text-center">
            <h3 className="text-base font-semibold text-emerald-400">Zero issues detected</h3>
            <p className="text-sm text-gray-400 mt-1">This pull request adheres cleanly to all quality standards.</p>
          </div>
        )}
      </div>

      {/* Interactive Floating ChatBot */}
      <PRChatBot reviewId={review.id} />
    </div>
  );
}
