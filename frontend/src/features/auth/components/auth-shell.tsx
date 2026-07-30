import * as React from "react";

export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid min-h-svh grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,480px)]">
      <div className="relative hidden overflow-hidden bg-sidebar lg:flex lg:flex-col lg:justify-between lg:p-12">
        <TraceMotif />
        <div className="relative z-10 flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-sm font-bold text-primary-foreground">
            R
          </div>
          <span className="font-mono text-sm font-medium tracking-wide text-sidebar-foreground">
            research-assistant
          </span>
        </div>

        <div className="relative z-10 max-w-md">
          <h1 className="text-3xl font-semibold leading-tight text-sidebar-foreground">
            Five agents. One trace.
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-sidebar-muted">
            Retrieval, memory, orchestration, and reasoning working together — every
            answer comes with the evidence and the decision path that produced it.
          </p>
        </div>

        <div className="relative z-10 flex gap-6 font-mono text-xs text-sidebar-muted">
          <span>semantic retrieval</span>
          <span>·</span>
          <span>long-term memory</span>
          <span>·</span>
          <span>agent orchestration</span>
        </div>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-xs font-bold text-primary-foreground">
              R
            </div>
            <span className="font-mono text-sm font-medium tracking-wide">research-assistant</span>
          </div>
          <h2 className="text-xl font-semibold text-foreground">{title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
          <div className="mt-6">{children}</div>
        </div>
      </div>
    </div>
  );
}

/**
 * The recurring "agent trace" motif: nodes joined by dotted connectors,
 * echoed later in the orchestration execution graph and research
 * reasoning trace. Here it's ambient background texture only.
 */
function TraceMotif() {
  const nodes = [
    [40, 90],
    [140, 60],
    [230, 130],
    [330, 70],
    [420, 150],
    [120, 220],
    [260, 260],
    [380, 290],
  ];
  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.16]"
      viewBox="0 0 480 420"
      fill="none"
      aria-hidden="true"
    >
      {nodes.slice(1).map((n, i) => (
        <line
          key={i}
          x1={nodes[i][0]}
          y1={nodes[i][1]}
          x2={n[0]}
          y2={n[1]}
          stroke="var(--sidebar-foreground)"
          strokeWidth="1"
          strokeDasharray="2 5"
        />
      ))}
      {nodes.map(([x, y], i) => (
        <circle
          key={i}
          cx={x}
          cy={y}
          r={i % 3 === 0 ? 5 : 3}
          fill={i % 3 === 0 ? "var(--sidebar-primary)" : "var(--sidebar-foreground)"}
        />
      ))}
    </svg>
  );
}
