"use client";

import { useEffect, useRef } from "react";

interface DimensionScore {
  dimension: string;
  score: number;
  finding_count: number;
  blocking_count: number;
  emoji: string;
}

interface HealthScoreProps {
  total: number;
  grade: string;
  recommendation: string;
  dimensions: DimensionScore[];
  totalFindings: number;
  totalBlocking: number;
}

function gradeColor(grade: string): string {
  if (grade === "A+" || grade === "A") return "#22c55e";
  if (grade === "B") return "#84cc16";
  if (grade === "C") return "#eab308";
  if (grade === "D") return "#f97316";
  return "#ef4444";
}

function gradeGlow(grade: string): string {
  if (grade === "A+" || grade === "A") return "0 0 32px rgba(34, 197, 94, 0.35)";
  if (grade === "B") return "0 0 32px rgba(132, 204, 22, 0.35)";
  if (grade === "C") return "0 0 32px rgba(234, 179, 8, 0.35)";
  return "0 0 32px rgba(239, 68, 68, 0.35)";
}

export function HealthScoreGauge({
  total,
  grade,
  recommendation,
  dimensions,
  totalFindings,
  totalBlocking,
}: HealthScoreProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    const cx = W / 2;
    const cy = H * 0.7;
    const R = Math.min(W, H) * 0.38;
    const startAngle = Math.PI;
    const endAngle = 2 * Math.PI;
    const progress = (total / 100) * Math.PI;

    ctx.clearRect(0, 0, W, H);

    // Background arc
    ctx.beginPath();
    ctx.arc(cx, cy, R, startAngle, endAngle);
    ctx.lineWidth = 18;
    ctx.strokeStyle = "rgba(255,255,255,0.06)";
    ctx.stroke();

    // Progress arc
    const color = gradeColor(grade);
    const grad = ctx.createLinearGradient(cx - R, cy, cx + R, cy);
    grad.addColorStop(0, color);
    grad.addColorStop(1, color + "99");
    ctx.beginPath();
    ctx.arc(cx, cy, R, startAngle, startAngle + progress);
    ctx.lineWidth = 18;
    ctx.lineCap = "round";
    ctx.strokeStyle = grad;
    ctx.stroke();

    // Score text
    ctx.fillStyle = color;
    ctx.font = `bold ${Math.floor(R * 0.52)}px Inter, system-ui`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(total.toFixed(0), cx, cy - R * 0.08);

    // Label
    ctx.fillStyle = "rgba(255,255,255,0.45)";
    ctx.font = `${Math.floor(R * 0.2)}px Inter, system-ui`;
    ctx.fillText("/ 100", cx, cy + R * 0.22);
  }, [total, grade]);

  const color = gradeColor(grade);

  return (
    <div
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "16px",
        padding: "24px",
        display: "flex",
        flexDirection: "column",
        gap: "20px",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <span style={{ fontSize: "20px" }}>🏥</span>
        <h3
          style={{
            margin: 0,
            fontSize: "16px",
            fontWeight: 600,
            color: "rgba(255,255,255,0.9)",
          }}
        >
          PR Health Score
        </h3>
        <span
          style={{
            marginLeft: "auto",
            fontSize: "24px",
            fontWeight: 800,
            color,
            textShadow: gradeGlow(grade),
          }}
        >
          {grade}
        </span>
      </div>

      {/* Gauge Canvas */}
      <canvas
        ref={canvasRef}
        width={240}
        height={140}
        style={{ width: "100%", maxWidth: "240px", alignSelf: "center" }}
      />

      {/* Recommendation */}
      <p
        style={{
          margin: 0,
          fontSize: "13px",
          color: "rgba(255,255,255,0.6)",
          textAlign: "center",
          lineHeight: 1.5,
        }}
      >
        {recommendation}
      </p>

      {/* Dimension breakdown */}
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {dimensions.map((dim) => (
          <div key={dim.dimension}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "4px",
              }}
            >
              <span
                style={{
                  fontSize: "12px",
                  color: "rgba(255,255,255,0.7)",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                {dim.emoji} {dim.dimension.charAt(0).toUpperCase() + dim.dimension.slice(1)}
              </span>
              <span
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  color: gradeColor(dim.score >= 90 ? "A" : dim.score >= 75 ? "B" : dim.score >= 60 ? "C" : "F"),
                }}
              >
                {dim.score.toFixed(0)}/100
              </span>
            </div>
            <div
              style={{
                height: "4px",
                background: "rgba(255,255,255,0.06)",
                borderRadius: "99px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${dim.score}%`,
                  background: gradeColor(dim.score >= 90 ? "A" : dim.score >= 75 ? "B" : dim.score >= 60 ? "C" : "F"),
                  borderRadius: "99px",
                  transition: "width 0.8s cubic-bezier(0.34,1.56,0.64,1)",
                }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Quick stats */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "8px",
          paddingTop: "4px",
        }}
      >
        {[
          { label: "Total Findings", value: totalFindings, emoji: "📋" },
          { label: "Blocking", value: totalBlocking, emoji: "🚫", danger: totalBlocking > 0 },
        ].map((stat) => (
          <div
            key={stat.label}
            style={{
              background: "rgba(255,255,255,0.04)",
              border: `1px solid ${stat.danger ? "rgba(239,68,68,0.3)" : "rgba(255,255,255,0.06)"}`,
              borderRadius: "10px",
              padding: "10px 12px",
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: "18px", marginBottom: "4px" }}>{stat.emoji}</div>
            <div
              style={{
                fontSize: "20px",
                fontWeight: 700,
                color: stat.danger ? "#ef4444" : "rgba(255,255,255,0.9)",
              }}
            >
              {stat.value}
            </div>
            <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.4)" }}>
              {stat.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
