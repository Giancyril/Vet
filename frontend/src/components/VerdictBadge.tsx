import { CheckCircle2, AlertOctagon, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

interface VerdictBadgeProps {
  verdict: "APPROVE" | "COMMENT" | "REQUEST_CHANGES" | string;
  size?: "sm" | "md";
}

export function VerdictBadge({ verdict, size = "md" }: VerdictBadgeProps) {
  if (verdict === "APPROVE") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 font-medium rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30",
          size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-xs"
        )}
      >
        <CheckCircle2 className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />
        Approved
      </span>
    );
  }

  if (verdict === "REQUEST_CHANGES") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 font-medium rounded-full bg-red-500/10 text-red-400 border border-red-500/30",
          size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-xs"
        )}
      >
        <AlertOctagon className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />
        Changes Requested
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 font-medium rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/30",
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-xs"
      )}
    >
      <MessageSquare className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />
      Commented
    </span>
  );
}
