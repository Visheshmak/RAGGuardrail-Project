import React, { useState } from "react";

export interface DataPoint {
  label: string;
  value: number; // e.g. 0.0 - 1.0 or custom
  secondaryValue?: number;
  date?: string;
}

interface MetricTrendChartProps {
  title: string;
  data: DataPoint[];
  metricName?: string;
  color?: string; // hex or tailwind stroke
  unit?: string;
  height?: number;
}

export function MetricTrendChart({
  title,
  data,
  metricName = "Score",
  color = "#6366f1", // Indigo
  unit = "%",
  height = 180,
}: MetricTrendChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center border border-dashed border-slate-800 rounded-xl bg-slate-900/30 text-xs text-slate-500"
        style={{ height }}
      >
        No historical evaluation runs yet
      </div>
    );
  }

  // Calculate coordinates
  const paddingX = 40;
  const paddingY = 30;
  const width = 500;
  const chartWidth = width - paddingX * 2;
  const chartHeight = height - paddingY * 2;

  const values = data.map((d) => d.value);
  const minVal = Math.min(...values, 0);
  const maxVal = Math.max(...values, 1);
  const range = maxVal - minVal || 1;

  const points = data.map((d, i) => {
    const x = paddingX + (i / Math.max(data.length - 1, 1)) * chartWidth;
    const y = paddingY + chartHeight - ((d.value - minVal) / range) * chartHeight;
    return { x, y, ...d };
  });

  const pathD = points.reduce((acc, p, i) => {
    return i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
  }, "");

  // Area under path
  const areaD =
    points.length > 0
      ? `${pathD} L ${points[points.length - 1].x} ${paddingY + chartHeight} L ${points[0].x} ${paddingY + chartHeight} Z`
      : "";

  return (
    <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/60 backdrop-blur-sm">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">{title}</h4>
        {hoveredIdx !== null && (
          <span className="text-xs font-mono font-bold text-indigo-400">
            {metricName}: {(data[hoveredIdx].value * 100).toFixed(1)}
            {unit} ({data[hoveredIdx].label})
          </span>
        )}
      </div>

      <div className="relative w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto overflow-visible"
          style={{ maxHeight: height }}
        >
          <defs>
            <linearGradient id={`grad-${title.replace(/\s+/g, "")}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.35" />
              <stop offset="100%" stopColor={color} stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid horizontal lines */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((step, idx) => {
            const y = paddingY + chartHeight - step * chartHeight;
            return (
              <g key={idx}>
                <line
                  x1={paddingX}
                  y1={y}
                  x2={width - paddingX}
                  y2={y}
                  stroke="#334155"
                  strokeDasharray="3 3"
                  strokeWidth="0.75"
                />
                <text
                  x={paddingX - 8}
                  y={y + 3}
                  textAnchor="end"
                  className="text-[9px] fill-slate-500 font-mono"
                >
                  {(minVal + step * range) * 100}%
                </text>
              </g>
            );
          })}

          {/* Fill area */}
          <path d={areaD} fill={`url(#grad-${title.replace(/\s+/g, "")})`} />

          {/* Trend Line */}
          <path d={pathD} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" />

          {/* Data Points */}
          {points.map((p, idx) => (
            <g
              key={idx}
              className="cursor-pointer group"
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
            >
              <circle
                cx={p.x}
                cy={p.y}
                r={hoveredIdx === idx ? 5 : 3.5}
                fill="#0f172a"
                stroke={color}
                strokeWidth={hoveredIdx === idx ? 3 : 2}
                className="transition-all"
              />
            </g>
          ))}
        </svg>
      </div>

      <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-2 pt-2 border-t border-slate-800/40">
        <span>{data[0]?.label || ""}</span>
        <span>{data[data.length - 1]?.label || ""}</span>
      </div>
    </div>
  );
}
