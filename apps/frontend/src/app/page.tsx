"use client";

import * as React from "react";
import Link from "next/link";
import {
  ArrowRight,
  Boxes,
  GitFork,
  MessageSquareText,
  ScanSearch,
  Workflow,
} from "lucide-react";

import { RepoGraphMark, Wordmark } from "@/components/brand";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

function Constellation({ className }: { className?: string }) {
  const nodes = React.useMemo(
    () =>
      Array.from({ length: 26 }, (_, i) => {
        const angle = (i / 26) * Math.PI * 2 + Math.sin(i * 1.7) * 0.4;
        const radius = 34 + ((i * 37) % 52);
        const x = 200 + Math.cos(angle) * radius;
        const y = 130 + Math.sin(angle) * radius * 0.75;
        return { x, y, i, r: (i % 5) + 2 };
      }),
    []
  );
  const lines = React.useMemo(() => {
    const out: { x1: number; y1: number; x2: number; y2: number; d: number }[] = [];
    for (let a = 0; a < nodes.length; a++) {
      for (let b = a + 1; b < nodes.length; b++) {
        const dx = nodes[a].x - nodes[b].x;
        const dy = nodes[a].y - nodes[b].y;
        const d = Math.hypot(dx, dy);
        if (d < 42 && (a * 13 + b * 7) % 5 < 2) {
          out.push({
            x1: nodes[a].x,
            y1: nodes[a].y,
            x2: nodes[b].x,
            y2: nodes[b].y,
            d,
          });
        }
      }
    }
    return out.sort((a, b) => a.d - b.d).slice(0, 48);
  }, [nodes]);

  return (
    <svg
      viewBox="0 0 400 260"
      className={className}
      role="img"
      aria-label="Animated call-graph constellation"
    >
      <defs>
        <radialGradient id="const-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="hsl(199 100% 66%)" stopOpacity="0.14" />
          <stop offset="100%" stopColor="hsl(199 100% 66%)" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#const-glow)" />
      {lines.map((l, i) => (
        <line
          key={i}
          x1={l.x1}
          y1={l.y1}
          x2={l.x2}
          y2={l.y2}
          stroke="hsl(199 100% 66%)"
          strokeOpacity={0.18 + (i % 3) * 0.08}
          strokeWidth="0.8"
        />
      ))}
      {nodes.map((n, i) => (
        <circle
          key={i}
          cx={n.x}
          cy={n.y}
          r={n.r}
          fill={
            i % 7 === 0
              ? "hsl(4 100% 68%)"
              : i % 3 === 0
                ? "hsl(39 100% 65%)"
                : "hsl(199 100% 66%)"
          }
          fillOpacity="0.9"
          className="animate-pulse-dot"
          style={{ animationDelay: `${(i % 7) * 0.22}s` }}
        />
      ))}
    </svg>
  );
}

const pipeline = [
  { n: "01", name: "Ingest", desc: "GitHub OAuth or local path" },
  { n: "02", name: "Parse", desc: "Tree-sitter AST, per symbol" },
  { n: "03", name: "Graph", desc: "Neo4j symbol graph" },
  { n: "04", name: "Embed", desc: "structural chunks → Qdrant" },
  { n: "05", name: "Retrieve", desc: "vector + symbol + graph" },
  { n: "06", name: "Answer", desc: "GraphRAG, cited context" },
];

const capabilities = [
  {
    icon: GitFork,
    title: "Symbol graph",
    body: "Functions, classes and modules as first-class nodes. CALLS, CONTAINS, INHERITS and IMPORTS edges derived deterministically from the AST — no LLM involved.",
  },
  {
    icon: Boxes,
    title: "Hybrid retrieval",
    body: "Four searchers fused into one ranked result set: vector similarity, exact symbol lookup, keyword match and graph traversal. Every hit cites its source.",
  },
  {
    icon: MessageSquareText,
    title: "GraphRAG answers",
    body: "Questions are grounded in retrieved symbols and graph context, so answers come with file:line citations. No key configured? You still get deterministic retrieval.",
  },
];

const telemetry = [
  { k: "symbols indexed", v: "218" },
  { k: "relationships", v: "262" },
  { k: "files parsed", v: "58" },
  { k: "pipeline jobs", v: "3 ✓" },
];

export default function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-x-clip">
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center gap-6 px-4 lg:px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <RepoGraphMark className="size-7 text-primary" />
            <Wordmark />
          </Link>
          <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
            <Link href="/#pipeline" className="transition-colors hover:text-foreground">
              Pipeline
            </Link>
            <Link href="/#capabilities" className="transition-colors hover:text-foreground">
              Capabilities
            </Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="transition-colors hover:text-foreground"
            >
              GitHub
            </a>
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <Badge variant="outline" className="hidden gap-1.5 font-data text-[10px] sm:flex">
              <span className="size-1.5 rounded-full bg-emerald-400" />
              self-hosted · OSS
            </Badge>
            <Button asChild size="sm" className="font-data text-xs">
              <Link href="/dashboard">
                Open dashboard <ArrowRight className="size-3.5" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <section className="blueprint-grid relative">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />
        <div className="mx-auto grid w-full max-w-6xl gap-10 px-4 pb-20 pt-16 md:grid-cols-2 md:items-center md:pt-24 lg:px-6">
          <div className="animate-fade-up">
            <p className="font-data text-[11px] uppercase tracking-[0.25em] text-primary">
              GraphRAG · self-hosted · BYOK
            </p>
            <h1 className="font-display mt-4 text-4xl font-semibold leading-[1.05] tracking-tight md:text-6xl">
              Your repository,
              <br />
              <span className="text-primary">mapped</span> and understood.
            </h1>
            <p className="mt-5 max-w-md text-base leading-relaxed text-muted-foreground">
              Repograph is an AI operating system for repositories: deterministic
              AST parsing builds a symbol graph, hybrid retrieval finds evidence,
              and GraphRAG answers questions with file:line citations — never
              hallucinations.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button asChild size="lg" className="font-data text-sm">
                <Link href="/dashboard">
                  Start indexing <ArrowRight className="size-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="font-data text-sm">
                <Link href="/#pipeline">How it works</Link>
              </Button>
            </div>
            <div className="mt-8 grid grid-cols-3 gap-6">
              {telemetry.map((t) => (
                <div key={t.k}>
                  <div className="font-display text-2xl font-semibold tabular-nums text-foreground">
                    {t.v}
                  </div>
                  <div className="mt-0.5 font-data text-[10px] uppercase tracking-widest text-muted-foreground">
                    {t.k}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="relative animate-fade-up [animation-delay:150ms]">
            <div className="absolute -inset-4 rounded-2xl bg-primary/5 blur-2xl" />
            <div className="relative overflow-hidden rounded-xl border border-border/80 bg-card/70 backdrop-blur glow-cyan">
              <div className="flex items-center gap-2 border-b border-border/60 px-4 py-2.5">
                <span className="size-2.5 rounded-full bg-chart-2/70" />
                <span className="size-2.5 rounded-full bg-chart-3/70" />
                <span className="size-2.5 rounded-full bg-chart-4/70" />
                <span className="ml-2 font-data text-[10px] uppercase tracking-widest text-muted-foreground">
                  explorer — app/core/security.py
                </span>
              </div>
              <Constellation className="h-auto w-full" />
              <div className="flex items-center justify-between border-t border-border/60 px-4 py-2.5 font-data text-[10px] text-muted-foreground">
                <span>218 symbols · 262 edges</span>
                <span className="text-chart-1">live from Neo4j</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="pipeline" className="border-t border-border/60">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 lg:px-6">
          <p className="font-data text-[11px] uppercase tracking-[0.25em] text-primary">
            the pipeline
          </p>
          <h2 className="font-display mt-3 max-w-lg text-2xl font-semibold tracking-tight md:text-3xl">
            Deterministic first. AI second.
          </h2>
          <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            {pipeline.map((p) => (
              <div
                key={p.n}
                className="group relative flex flex-col gap-2 rounded-md border border-border/70 bg-card/50 p-4 transition-colors hover:border-primary/50"
              >
                <span className="font-data text-[10px] text-primary">{p.n}</span>
                <span className="font-display text-sm font-semibold">{p.name}</span>
                <span className="font-data text-[10px] leading-relaxed text-muted-foreground">
                  {p.desc}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-6 flex flex-wrap gap-2">
            {[
              "no naive token splitting",
              "retries · health checks · observability",
              "one-command docker compose up",
            ].map((t) => (
              <Badge key={t} variant="outline" className="font-data text-[10px]">
                {t}
              </Badge>
            ))}
          </div>
        </div>
      </section>

      <section id="capabilities" className="border-t border-border/60 bg-card/30">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 lg:px-6">
          <p className="font-data text-[11px] uppercase tracking-[0.25em] text-primary">
            capabilities
          </p>
          <h2 className="font-display mt-3 max-w-lg text-2xl font-semibold tracking-tight md:text-3xl">
            Built for understanding, not codegen.
          </h2>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {capabilities.map((c) => (
              <div
                key={c.title}
                className="flex flex-col gap-4 rounded-md border border-border/70 bg-card/70 p-6 transition-colors hover:border-primary/40"
              >
                <c.icon className="size-6 text-primary" />
                <h3 className="font-display text-base font-semibold">{c.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {c.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-border/60">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center gap-6 px-4 py-16 text-center lg:px-6">
          <Workflow className="size-8 text-primary" />
          <h2 className="font-display max-w-xl text-2xl font-semibold tracking-tight md:text-3xl">
            From local checkout to answered questions in one command.
          </h2>
          <div className="w-full max-w-xl overflow-hidden rounded-md border border-border/70 text-left">
            <div className="flex items-center gap-2 border-b border-border/60 bg-muted/40 px-4 py-2 font-data text-[10px] uppercase tracking-widest text-muted-foreground">
              terminal
            </div>
            <pre className="overflow-x-auto p-4 font-data text-xs leading-relaxed">
              <code>
                <span className="text-muted-foreground">$</span> docker compose up -d
                <br />
                <span className="text-muted-foreground">$</span> repograph add ./apps/api
                <br />
                <span className="text-chart-1">✓ snapshot</span>{" "}
                <span className="text-chart-1">✓ parse</span>{" "}
                <span className="text-chart-1">✓ graph</span>{" "}
                <span className="text-muted-foreground">· embed (needs key)</span>
                <br />
                <span className="text-muted-foreground">$</span> repograph ask "how does
                create_access_token work?"
              </code>
            </pre>
          </div>
          <Button asChild size="lg" className="font-data text-sm">
            <Link href="/dashboard">
              Open the dashboard <ArrowRight className="size-4" />
            </Link>
          </Button>
        </div>
      </section>

      <footer className="border-t border-border/60">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center gap-3 px-4 py-8 sm:flex-row lg:px-6">
          <div className="flex items-center gap-2.5">
            <RepoGraphMark className="size-5 text-primary" />
            <Wordmark className="text-sm" />
          </div>
          <p className="font-data text-[10px] uppercase tracking-widest text-muted-foreground sm:ml-4">
            AI operating system for repositories
          </p>
          <div className="ml-auto flex items-center gap-4 font-data text-[10px] text-muted-foreground">
            <ScanSearch className="size-3.5" />
            <span>self-hosted · Apache 2.0</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
