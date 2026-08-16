"use client";
import { useEffect, useRef, useState } from "react";
import { Activity, Shield, Zap, Star, TestTube2, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";

interface StreamEvent {
  review_id: string;
  event: string;
  data: Record<string, unknown>;
  timestamp: number;
}

interface AgentStatus {
  name: string;
  icon: React.ReactNode;
  color: string;
  status: "idle" | "running" | "done" | "error";
  detail: string;
}

interface LiveAgentStreamProps {
  reviewId: string;
  onComplete?: (verdict: string) => void;
}

const AGENTS: AgentStatus[] = [
  { name: "Security Auditor", icon: <Shield size={16} />, color: "text-red-400", status: "idle", detail: "Waiting..." },
  { name: "Performance Architect", icon: <Zap size={16} />, color: "text-yellow-400", status: "idle", detail: "Waiting..." },
  { name: "Clean Code Guardian", icon: <Star size={16} />, color: "text-blue-400", status: "idle", detail: "Waiting..." },
  { name: "Test Coverage Specialist", icon: <TestTube2 size={16} />, color: "text-green-400", status: "idle", detail: "Waiting..." },
];

export function LiveAgentStream({ reviewId, onComplete }: LiveAgentStreamProps) {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [agents, setAgents] = useState<AgentStatus[]>(AGENTS);
  const [connected, setConnected] = useState(false);
  const [healthScore, setHealthScore] = useState<number | null>(null);
  const [grade, setGrade] = useState<string | null>(null);
  const [finished, setFinished] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const wsUrl = `ws://localhost:8000/api/v1/ws/reviews/${reviewId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      // Keep-alive heartbeat
      const interval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
      }, 15000);
      ws.onclose = () => clearInterval(interval);
    };

    ws.onmessage = (evt) => {
      const msg: StreamEvent = JSON.parse(evt.data);
      if (msg.event === "pong") return;

      setEvents((prev) => [...prev.slice(-49), msg]);

      if (msg.event === "agent_started") {
        const agent = msg.data.agent as string;
        setAgents((prev) => prev.map((a) =>
          a.name.toLowerCase().includes(agent?.split(" ")[0]?.toLowerCase() || "")
            ? { ...a, status: "running", detail: msg.data.description as string || "Analyzing..." }
            : a
        ));
      }

      if (msg.event === "finding_discovered") {
        setAgents((prev) => prev.map((a) =>
          a.status === "running"
            ? { ...a, detail: `Found: ${msg.data.title}` }
            : a
        ));
      }

      if (msg.event === "health_calculated") {
        setHealthScore(msg.data.score as number);
        setGrade(msg.data.grade as string);
        setAgents((prev) => prev.map((a) => ({ ...a, status: "done" })));
      }

      if (msg.event === "review_finished") {
        setFinished(true);
        onComplete?.(msg.data.verdict as string);
      }
    };

    ws.onerror = () => setConnected(false);
    ws.onclose = () => setConnected(false);

    return () => ws.close();
  }, [reviewId, onComplete]);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [events]);

  const statusIcon = (status: string) => {
    if (status === "running") return <Loader2 size={14} className="animate-spin text-blue-400" />;
    if (status === "done") return <CheckCircle2 size={14} className="text-green-400" />;
    if (status === "error") return <AlertTriangle size={14} className="text-red-400" />;
    return <div className="w-3.5 h-3.5 rounded-full border border-gray-600" />;
  };

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800/50">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-blue-400 animate-pulse" />
          <span className="text-sm font-semibold text-gray-100">Live Agent Activity</span>
        </div>
        <div className="flex items-center gap-2">
          {connected ? (
            <span className="flex items-center gap-1.5 text-xs text-green-400">
              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" /> Live
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs text-gray-500">
              <span className="w-2 h-2 rounded-full bg-gray-500" /> Disconnected
            </span>
          )}
          {healthScore !== null && (
            <span className="ml-2 px-2 py-0.5 bg-blue-900/50 border border-blue-700 rounded text-xs text-blue-300 font-mono">
              Health: {healthScore}/100 {grade}
            </span>
          )}
        </div>
      </div>

      {/* Agents Grid */}
      <div className="grid grid-cols-2 gap-2 p-4 border-b border-gray-700">
        {agents.map((agent) => (
          <div
            key={agent.name}
            className={`flex items-start gap-2.5 p-2.5 rounded-lg border transition-all duration-300 ${
              agent.status === "running"
                ? "bg-blue-950/30 border-blue-700"
                : agent.status === "done"
                ? "bg-green-950/20 border-green-800"
                : "bg-gray-800/40 border-gray-700"
            }`}
          >
            <div className="mt-0.5">{statusIcon(agent.status)}</div>
            <div className="min-w-0 flex-1">
              <div className={`text-xs font-medium ${agent.color}`}>{agent.name}</div>
              <div className="text-xs text-gray-400 truncate mt-0.5">{agent.detail}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Event Log */}
      <div
        ref={logRef}
        className="h-40 overflow-y-auto p-3 font-mono text-xs space-y-1 bg-black/30"
      >
        {events.length === 0 ? (
          <div className="text-gray-600 italic">Waiting for review events...</div>
        ) : (
          events.map((evt, i) => (
            <div key={i} className="flex gap-2 items-start">
              <span className="text-gray-600 shrink-0">
                {new Date(evt.timestamp * 1000).toLocaleTimeString()}
              </span>
              <span className={`shrink-0 ${
                evt.event === "finding_discovered" ? "text-yellow-400" :
                evt.event === "review_finished" ? "text-green-400" :
                evt.event === "secret_scanned" ? "text-red-400" :
                "text-blue-400"
              }`}>[{evt.event}]</span>
              <span className="text-gray-300 break-all">
                {JSON.stringify(evt.data)}
              </span>
            </div>
          ))
        )}
        {finished && (
          <div className="text-green-400 font-semibold mt-2">✓ Review complete</div>
        )}
      </div>
    </div>
  );
}
