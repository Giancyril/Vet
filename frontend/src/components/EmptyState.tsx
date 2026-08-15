import Link from "next/link";
import { Bot, GitPullRequest, ArrowRight, ShieldCheck, Terminal } from "lucide-react";

interface EmptyStateProps {
  type: "reviews" | "repos";
}

export function EmptyState({ type }: EmptyStateProps) {
  if (type === "reviews") {
    return (
      <div className="py-16 px-6 text-center max-w-lg mx-auto">
        <div className="w-16 h-16 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mx-auto mb-5 shadow-lg shadow-purple-500/5">
          <Bot className="w-8 h-8 text-purple-400" />
        </div>
        <h3 className="text-lg font-bold text-white mb-2">No Pull Request Reviews Yet</h3>
        <p className="text-sm text-gray-400 mb-6 leading-relaxed">
          Warden is actively listening for webhook events. Open or update a Pull Request on any connected GitHub repository to receive your automated Gemini AI review.
        </p>

        <div className="p-4 rounded-xl bg-surface-raised/60 border border-border text-left mb-6 text-xs text-gray-300 space-y-2">
          <div className="flex items-center gap-2 text-purple-400 font-semibold uppercase tracking-wider text-[10px]">
            <Terminal className="w-3.5 h-3.5" /> How to trigger a review
          </div>
          <ol className="list-decimal list-inside space-y-1 text-gray-400">
            <li>Create a new branch in your GitHub repo</li>
            <li>Make code changes and push commit</li>
            <li>Open a Pull Request &bull; Warden will analyze and comment</li>
          </ol>
        </div>

        <Link
          href="/repos"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-500/20 transition-all"
        >
          Check Connected Repositories <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    );
  }

  return (
    <div className="py-16 px-6 text-center max-w-lg mx-auto">
      <div className="w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mx-auto mb-5">
        <GitPullRequest className="w-8 h-8 text-blue-400" />
      </div>
      <h3 className="text-lg font-bold text-white mb-2">Connect Your First Repository</h3>
      <p className="text-sm text-gray-400 mb-6 leading-relaxed">
        Install the Warden GitHub App on your account or organization to enable automated AI code reviews on all your pull requests.
      </p>
      <a
        href="https://github.com/settings/apps"
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-500/20 transition-all"
      >
        Configure GitHub App <ArrowRight className="w-3.5 h-3.5" />
      </a>
    </div>
  );
}
