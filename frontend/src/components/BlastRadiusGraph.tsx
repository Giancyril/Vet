"use client";
import { useEffect, useRef, useState } from "react";
import { GitBranch, AlertOctagon, Zap, ChevronRight } from "lucide-react";

interface BlastRadiusData {
  review_id: string;
  modified_files: string[];
  downstream_files: string[];
  impact_index: number;
  impact_level: string;
  affected_endpoints: string[];
  breaking_exports: string[];
  summary: string;
  dependency_graph: Record<string, string[]>;
}

interface BlastRadiusGraphProps {
  data: BlastRadiusData;
}

const IMPACT_COLORS: Record<string, string> = {
  Low: "text-green-400 border-green-700 bg-green-950/30",
  Medium: "text-yellow-400 border-yellow-700 bg-yellow-950/30",
  High: "text-orange-400 border-orange-700 bg-orange-950/30",
  Critical: "text-red-400 border-red-700 bg-red-950/30",
};

const IMPACT_BAR_COLORS: Record<string, string> = {
  Low: "bg-green-500",
  Medium: "bg-yellow-500",
  High: "bg-orange-500",
  Critical: "bg-red-500",
};

function FileNode({ file, type }: { file: string; type: "modified" | "downstream" | "endpoint" | "breaking" }) {
  const colors: Record<string, string> = {
    modified: "bg-blue-900/40 border-blue-700 text-blue-300",
    downstream: "bg-gray-800 border-gray-600 text-gray-400",
    endpoint: "bg-purple-900/40 border-purple-700 text-purple-300",
    breaking: "bg-red-900/40 border-red-700 text-red-300",
  };

  const basename = file.split("/").pop() || file;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border font-mono ${colors[type]}`}
      title={file}
    >
      {basename}
    </span>
  );
}

export function BlastRadiusGraph({ data }: BlastRadiusGraphProps) {
  const impactColorClass = IMPACT_COLORS[data.impact_level] || IMPACT_COLORS.Low;
  const barColor = IMPACT_BAR_COLORS[data.impact_level] || IMPACT_BAR_COLORS.Low;

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800/50">
        <div className="flex items-center gap-2">
          <GitBranch size={16} className="text-purple-400" />
          <span className="text-sm font-semibold text-gray-100">PR Blast Radius</span>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-semibold ${impactColorClass}`}>
          <AlertOctagon size={12} />
          {data.impact_level} Impact — {data.impact_index}/100
        </div>
      </div>

      {/* Impact Score Bar */}
      <div className="px-4 pt-4 pb-2">
        <div className="flex justify-between text-xs text-gray-400 mb-1.5">
          <span>Blast Radius Index</span>
          <span className="font-mono font-semibold">{data.impact_index}/100</span>
        </div>
        <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${barColor}`}
            style={{ width: `${data.impact_index}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-gray-400">{data.summary}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 border-t border-gray-800">
        {/* Modified Files */}
        <div>
          <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-blue-400">
            <Zap size={12} /> Modified Files ({data.modified_files.length})
          </div>
          <div className="flex flex-wrap gap-1.5">
            {data.modified_files.length === 0 ? (
              <span className="text-xs text-gray-600 italic">None</span>
            ) : (
              data.modified_files.map((f) => <FileNode key={f} file={f} type="modified" />)
            )}
          </div>
        </div>

        {/* Breaking Exports */}
        <div>
          <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-red-400">
            <AlertOctagon size={12} /> Breaking Exports ({data.breaking_exports.length})
          </div>
          <div className="flex flex-wrap gap-1.5">
            {data.breaking_exports.length === 0 ? (
              <span className="text-xs text-green-500">✓ No breaking exports</span>
            ) : (
              data.breaking_exports.map((e) => <FileNode key={e} file={e} type="breaking" />)
            )}
          </div>
        </div>

        {/* Downstream Impact */}
        <div>
          <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-gray-400">
            <ChevronRight size={12} /> Downstream Modules ({data.downstream_files.length})
          </div>
          <div className="flex flex-wrap gap-1.5">
            {data.downstream_files.length === 0 ? (
              <span className="text-xs text-gray-600 italic">No downstream impact</span>
            ) : (
              data.downstream_files.slice(0, 8).map((f) => <FileNode key={f} file={f} type="downstream" />)
            )}
          </div>
        </div>

        {/* Affected Endpoints */}
        <div>
          <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-purple-400">
            <GitBranch size={12} /> API Endpoints ({data.affected_endpoints.length})
          </div>
          <div className="flex flex-wrap gap-1.5">
            {data.affected_endpoints.length === 0 ? (
              <span className="text-xs text-gray-600 italic">No endpoints affected</span>
            ) : (
              data.affected_endpoints.map((e) => <FileNode key={e} file={e} type="endpoint" />)
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
