"use client";

import * as React from "react";
import { Activity } from "lucide-react";

import { api, OverviewStats } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const stages = [
  {
    id: 1,
    name: "Snapshot",
    desc: "Capture a git revision with metadata.",
    color: "var(--chart-1)",
  },
  {
    id: 2,
    name: "Parse",
    desc: "Tree-sitter AST walk — symbols, relationships, modules.",
    color: "var(--chart-2)",
  },
  {
    id: 3,
    name: "Graph sync",
    desc: "Upsert symbol graph into Neo4j.",
    color: "var(--chart-3)",
  },
  {
    id: 4,
    name: "Embed",
    desc: "Structural chunks by symbol → Qdrant vectors.",
    color: "var(--chart-4)",
  },
  {
    id: 5,
    name: "Retrieve",
    desc: "Hybrid: vector + symbol + keyword + graph.",
    color: "var(--chart-5)",
  },
  {
    id: 6,
    name: "Answer",
    desc: "GraphRAG synthesis with cited context blocks.",
    color: "var(--chart-1)",
  },
];

export default function PipelinePage() {
  const [overview, setOverview] = React.useState<OverviewStats | null>(null);

  React.useEffect(() => {
    api
      .get<OverviewStats>("/repositories/stats/overview")
      .then(setOverview)
      .catch(() => {});
  }, []);

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 px-4 pt-4 lg:px-6">
      <div className="flex items-center gap-2">
        <Activity className="size-5 text-primary" />
        <div>
          <h1 className="font-display text-xl font-semibold">Indexing pipeline</h1>
          <p className="text-sm text-muted-foreground">
            Deterministic first, AI second. Each stage is a discrete job with
            retries and a terminal state.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="font-display text-base">Stages</CardTitle>
          <CardDescription className="font-data text-xs">
            jobs: {overview ? `${overview.jobs.completed} completed · ${overview.jobs.queued + overview.jobs.running} in flight · ${overview.jobs.failed} failed` : "…"}
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {stages.map((s) => (
            <div
              key={s.id}
              className="relative flex flex-col gap-2 overflow-hidden rounded-md border p-4"
            >
              <div
                className="absolute inset-y-0 left-0 w-0.5"
                style={{ background: s.color }}
              />
              <div className="flex items-center gap-2">
                <span
                  className="flex size-5 items-center justify-center rounded-sm font-data text-[10px] text-background"
                  style={{ background: s.color }}
                >
                  {s.id}
                </span>
                <span className="font-data text-sm font-medium">{s.name}</span>
              </div>
              <p className="text-xs text-muted-foreground">{s.desc}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="font-display text-base">Design invariants</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-2">
          <div className="rounded-md border px-3 py-2">
            <div className="font-data text-xs text-foreground">Structural chunking</div>
            <div className="mt-1 text-xs">
              chunks are functions, classes, modules — never naive token splits.
            </div>
          </div>
          <div className="rounded-md border px-3 py-2">
            <div className="font-data text-xs text-foreground">Graph-grounded context</div>
            <div className="mt-1 text-xs">
              retrieval produces citations; hallucinations are structurally
              prevented.
            </div>
          </div>
          <div className="rounded-md border px-3 py-2">
            <div className="font-data text-xs text-foreground">Pluggable providers</div>
            <div className="mt-1 text-xs">
              OpenAI, Anthropic, Ollama — bring your own key, or run
              retrieval-only.
            </div>
          </div>
          <div className="rounded-md border px-3 py-2">
            <div className="font-data text-xs text-foreground">Self-hosted</div>
            <div className="mt-1 text-xs">
              Postgres, Redis, Neo4j, Qdrant behind one <code className="font-data">docker compose up</code>.
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center gap-2 px-1">
        <Badge variant="outline" className="font-data text-[10px]">
          phases 0–9 in Workflow.md
        </Badge>
        <Badge variant="outline" className="font-data text-[10px]">
          GraphRAG: deterministic retrieval before any LLM call
        </Badge>
      </div>
    </div>
  );
}
