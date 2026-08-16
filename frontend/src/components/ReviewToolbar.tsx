"use client";
import { useState } from "react";
import { FileText, TestTube2, Sparkles, GitPullRequest } from "lucide-react";
import { CompanionPRModal } from "./CompanionPRModal";
import { ChangelogModal } from "./ChangelogModal";
import { TestGeneratorModal } from "./TestGeneratorModal";

interface ReviewToolbarProps {
  reviewId: string;
  prNumber: number;
  fixableCount: number;
}

export function ReviewToolbar({ reviewId, prNumber, fixableCount }: ReviewToolbarProps) {
  const [showChangelog, setShowChangelog] = useState(false);
  const [showTestGen, setShowTestGen] = useState(false);

  return (
    <div className="flex items-center gap-2.5 flex-wrap">
      {/* Changelog Generator Modal Button */}
      <button
        onClick={() => setShowChangelog(true)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-950/60 border border-indigo-700/60 text-indigo-300 hover:bg-indigo-900/60 hover:text-white transition-all shadow-sm"
      >
        <FileText className="w-3.5 h-3.5 text-indigo-400" />
        Changelog & Notes
      </button>

      {/* Test Generator Modal Button */}
      <button
        onClick={() => setShowTestGen(true)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-950/60 border border-emerald-700/60 text-emerald-300 hover:bg-emerald-900/60 hover:text-white transition-all shadow-sm"
      >
        <TestTube2 className="w-3.5 h-3.5 text-emerald-400" />
        Generate Tests
      </button>

      {/* Companion PR Modal */}
      <CompanionPRModal
        reviewId={reviewId}
        prNumber={prNumber}
        fixableCount={fixableCount}
      />

      {/* Modals */}
      {showChangelog && (
        <ChangelogModal
          reviewId={reviewId}
          prNumber={prNumber}
          onClose={() => setShowChangelog(false)}
        />
      )}

      {showTestGen && (
        <TestGeneratorModal
          reviewId={reviewId}
          prNumber={prNumber}
          onClose={() => setShowTestGen(false)}
        />
      )}
    </div>
  );
}
