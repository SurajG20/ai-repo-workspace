"use client";

import * as React from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import { toast } from "sonner";

import { api, CallEdge, RepositoryItem } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function hash(str: string): number {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967295;
}

function fileNameOf(id: string, file: string): string {
  return file.split("/").pop() ?? file;
}

function symbolNameOf(id: string, name: string): string {
  return name.length > 18 ? `${name.slice(0, 16)}…` : name;
}

const kindFromId = (id: string) => {
  const parts = id.split(":");
  const last = parts[parts.length - 1] ?? "";
  if (last.startsWith("class ")) return "class";
  if (last.startsWith("function ")) return "function";
  return "variable";
};

const nodeKindColor: Record<string, string> = {
  function: "var(--chart-1)",
  class: "var(--chart-4)",
  variable: "var(--chart-3)",
};

function SymbolNode({ data }: NodeProps<{ name: string; file: string; kind: string }>) {
  return (
    <div className="group flex flex-col rounded-md border border-sidebar-border bg-card px-3 py-2 shadow-sm transition-colors hover:border-chart-1/60">
      <Handle type="target" position={Position.Left} className="!size-1.5 !bg-chart-1" />
      <span className="font-data text-xs font-medium leading-tight">
        {symbolNameOf("", data.name)}
      </span>
      <span className="mt-0.5 flex items-center gap-1.5 font-data text-[10px] text-muted-foreground">
        <span
          className="inline-block size-1.5 rounded-full"
          style={{ background: nodeKindColor[data.kind] ?? "var(--muted-foreground)" }}
        />
        {fileNameOf("", data.file)}
      </span>
      <Handle type="source" position={Position.Right} className="!size-1.5 !bg-chart-1" />
    </div>
  );
}

const nodeTypes = { symbol: SymbolNode };

export default function ExplorerPage() {
  const [repos, setRepos] = React.useState<RepositoryItem[]>([]);
  const [repoId, setRepoId] = React.useState("");
  const [edges, setEdges] = React.useState<CallEdge[] | null>(null);
  const [depth, setDepth] = React.useState(2);
  const [selected, setSelected] = React.useState<string | null>(null);

  React.useEffect(() => {
    api
      .get<RepositoryItem[]>("/repositories")
      .then((r) => {
        setRepos(r);
        if (r.length) setRepoId(r[0].id);
      })
      .catch(() => {});
  }, []);

  React.useEffect(() => {
    if (!repoId) return;
    let cancelled = false;
    setEdges(null);
    api
      .get<CallEdge[] | { edges: CallEdge[] }>(
        `/repositories/${repoId}/graph/call-graph?depth=${depth}&limit=500`
      )
      .then((res) => {
        if (!cancelled) setEdges(Array.isArray(res) ? res : res.edges ?? []);
      })
      .catch((e) => {
        if (!cancelled) {
          toast(e.message);
          setEdges([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [repoId, depth]);

  const { nodes, flowEdges } = React.useMemo(() => {
    const list = edges ?? [];
    const nodes: Node[] = [];
    const map = new Map<string, CallEdge>();

    for (const e of list) {
      if (!map.has(e.source_id)) map.set(e.source_id, e);
      if (!map.has(e.target_id)) map.set(e.target_id, e);
    }

    const ids = Array.from(map.keys());
    ids.forEach((id, i) => {
      const info = map.get(id)!;
      const isSource = info.source_id === id;
      const name = isSource ? info.source_name : info.target_name;
      const file = isSource ? info.source_file : info.target_file;
      const angle = (i / Math.max(ids.length, 1)) * Math.PI * 2;
      const radius = 160 + hash(id) * 220;
      nodes.push({
        id,
        type: "symbol",
        position: {
          x: Math.cos(angle) * radius,
          y: Math.sin(angle) * radius * 0.8,
        },
        data: { name, file, kind: kindFromId(id) },
      });
    });

    const flowEdges: Edge[] = list.map((e, i) => ({
      id: `e${i}`,
      source: e.source_id,
      target: e.target_id,
      type: "smoothstep",
      animated: e.distance <= depth,
      markerEnd: { type: MarkerType.ArrowClosed, color: "hsl(var(--chart-1))" },
      style: {
        stroke: "hsl(var(--chart-1))",
        strokeOpacity: e.distance === 1 ? 0.9 : 0.35,
        strokeWidth: e.distance === 1 ? 1.4 : 1,
      },
    }));

    return { nodes, flowEdges: flowEdges };
  }, [edges, depth]);

  const selectedEdge = edges?.find(
    (e) => e.source_id === selected || e.target_id === selected
  );
  const selectedIsSource = selectedEdge?.source_id === selected;

  return (
    <div className="flex h-[calc(100dvh-3rem)] flex-col gap-3 px-4 pt-4 lg:px-6">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="mr-auto font-display text-xl font-semibold">Explorer</h1>
        <Select value={repoId} onValueChange={setRepoId}>
          <SelectTrigger className="h-8 w-44 font-data text-xs">
            <SelectValue placeholder="repository" />
          </SelectTrigger>
          <SelectContent>
            {repos.map((r) => (
              <SelectItem key={r.id} value={r.id} className="font-data text-xs">
                {r.full_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex gap-1 rounded-md border p-0.5">
          {[1, 2, 3, 6].map((d) => (
            <Button
              key={d}
              variant="ghost"
              size="sm"
              onClick={() => setDepth(d)}
              className={cn(
                "h-7 px-2.5 font-data text-xs",
                depth === d && "bg-primary/15 text-primary"
              )}
            >
              d{d}
            </Button>
          ))}
        </div>
      </div>

      <div className="relative flex-1 overflow-hidden rounded-lg border blueprint-grid-lg">
        {edges === null ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <Skeleton className="h-full w-full rounded-none" />
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            proOptions={{ hideAttribution: true }}
            onNodeClick={(_, node) => setSelected(node.id)}
            nodesDraggable
            panOnScroll
            minZoom={0.2}
            maxZoom={2}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={24}
              size={1}
              color="rgba(90, 200, 255, 0.18)"
            />
            <Controls className="!border-sidebar-border !bg-card" />
          </ReactFlow>
        )}
        <div className="pointer-events-none absolute bottom-3 left-3 rounded-md border bg-background/80 px-3 py-2 backdrop-blur">
          <div className="font-data text-[10px] uppercase tracking-widest text-muted-foreground">
            call graph
          </div>
          <div className="font-data text-xs">
            {edges ? `${nodes.length} symbols · ${flowEdges.length} calls` : "…"}
          </div>
        </div>
        {selected && selectedEdge ? (
          <div className="absolute right-3 top-3 w-72 rounded-lg border bg-background/90 p-4 backdrop-blur">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="font-data text-sm font-medium">
                  {selectedIsSource
                    ? selectedEdge.source_name
                    : selectedEdge.target_name}
                </div>
                <div className="mt-1 font-data text-[11px] text-muted-foreground">
                  {selectedIsSource ? selectedEdge.source_file : selectedEdge.target_file}
                </div>
              </div>
              <Badge variant="outline" className="font-data text-[10px]">
                {selectedIsSource ? "caller" : "callee"}
              </Badge>
            </div>
            <div className="mt-3 grid gap-1 border-t pt-2 font-data text-[11px] text-muted-foreground">
              <div className="flex justify-between">
                <span>target</span>
                <span className="text-foreground">
                  {selectedIsSource ? selectedEdge.target_name : selectedEdge.source_name}
                </span>
              </div>
              <div className="flex justify-between">
                <span>distance</span>
                <span className="text-foreground">{selectedEdge.distance} hop(s)</span>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
