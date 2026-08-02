"use client";

import * as React from "react";
import { CartesianGrid, Area, AreaChart, XAxis, YAxis } from "recharts";
import { GitBranch } from "lucide-react";

import { api, CallEdge } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";

const chartConfig = {
  edges: {
    label: "edges",
    color: "hsl(var(--chart-1))",
  },
  cumulative: {
    label: "cumulative",
    color: "hsl(var(--chart-2))",
  },
} satisfies Record<string, { label: string; color: string }>;

function buildDepthData(edges: CallEdge[], maxDepth: number) {
  const dist = Array.from({ length: maxDepth }, (_, i) => ({
    depth: i + 1,
    edges: 0,
  }));
  for (const e of edges) {
    const i = Math.min(e.distance, maxDepth) - 1;
    if (i >= 0) dist[i].edges += 1;
  }
  let acc = 0;
  return dist.map((d) => ({
    ...d,
    cumulative: (acc += d.edges),
  }));
}

export function ChartAreaInteractive({
  repositoryId,
}: {
  repositoryId?: string;
}) {
  const [edges, setEdges] = React.useState<CallEdge[] | null>(null);
  const [maxDepth, setMaxDepth] = React.useState(3);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setEdges(null);
    setError(null);
    const query = repositoryId
      ? `?repository_id=${repositoryId}&depth=6&limit=500`
      : `?depth=6&limit=500`;
    api
      .get<CallEdge[] | { edges: CallEdge[] }>(`/graph/call-graph${query}`)
      .then((res) => {
        if (cancelled) return;
        setEdges(Array.isArray(res) ? res : res.edges ?? []);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [repositoryId]);

  const data = edges ? buildDepthData(edges, maxDepth) : null;
  const total = edges?.length ?? 0;

  return (
    <Card>
      <CardHeader className="flex flex-col items-stretch space-y-0 border-b p-0 sm:flex-row">
        <div className="flex flex-1 flex-col justify-center gap-1 px-6 py-5 sm:py-6">
          <CardTitle className="flex items-center gap-2">
            <GitBranch className="size-4 text-primary" />
            Call-graph reachability
          </CardTitle>
          <CardDescription>
            Distribution of edges by traversal depth — how deep the call graph
            runs from any entry point.
          </CardDescription>
        </div>
        <div className="flex">
          <button
            onClick={() => setMaxDepth(1)}
            data-active={maxDepth === 1}
            className="relative z-30 flex flex-1 flex-col justify-center gap-1 border-t px-6 py-4 text-left transition-colors data-[active=true]:bg-muted/40 sm:w-28 sm:border-l sm:border-t-0"
          >
            <span className="font-data text-xs text-muted-foreground">Depth</span>
            <span className="font-display text-lg font-semibold tabular-nums">1 hop</span>
          </button>
          <button
            onClick={() => setMaxDepth(3)}
            data-active={maxDepth === 3}
            className="relative z-30 flex flex-1 flex-col justify-center gap-1 border-t px-6 py-4 text-left transition-colors data-[active=true]:bg-muted/40 sm:w-28 sm:border-l sm:border-t-0"
          >
            <span className="font-data text-xs text-muted-foreground">Depth</span>
            <span className="font-display text-lg font-semibold tabular-nums">3 hops</span>
          </button>
          <button
            onClick={() => setMaxDepth(6)}
            data-active={maxDepth === 6}
            className="relative z-30 flex flex-1 flex-col justify-center gap-1 border-t px-6 py-4 text-left transition-colors data-[active=true]:bg-muted/40 sm:w-28 sm:border-l sm:border-t-0"
          >
            <span className="font-data text-xs text-muted-foreground">Depth</span>
            <span className="font-display text-lg font-semibold tabular-nums">6 hops</span>
          </button>
        </div>
      </CardHeader>
      <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6">
        {error ? (
          <div className="flex h-64 items-center justify-center font-data text-sm text-muted-foreground">
            {error}
          </div>
        ) : data === null ? (
          <div className="flex h-64 flex-col gap-3 px-4 pt-4">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-56 w-full" />
          </div>
        ) : (
          <ChartContainer
            config={chartConfig}
            className="aspect-auto h-[280px] w-full"
          >
            <AreaChart
              data={data}
              margin={{ left: -16, right: 8, top: 8 }}
              accessibilityLayer
            >
              <CartesianGrid vertical={false} stroke="hsl(var(--border))" strokeDasharray="4 4" />
              <XAxis
                dataKey="depth"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => `d${v}`}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                tick={{ fontSize: 11 }}
              />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Area
                dataKey="edges"
                type="monotone"
                fill="var(--color-edges)"
                fillOpacity={0.35}
                stroke="var(--color-edges)"
                strokeWidth={1.5}
              />
              <Area
                dataKey="cumulative"
                type="monotone"
                fill="var(--color-cumulative)"
                fillOpacity={0.08}
                stroke="var(--color-cumulative)"
                strokeWidth={1.2}
              />
              <ChartLegend content={<ChartLegendContent />} />
            </AreaChart>
          </ChartContainer>
        )}
      </CardContent>
      <div className="border-t px-6 py-3">
        <div className="font-data text-xs text-muted-foreground">
          {edges
            ? `${total} edges sampled · derived from Neo4j traversal at depth ≤ 6`
            : "sampling Neo4j traversal…"}
        </div>
      </div>
    </Card>
  );
}
