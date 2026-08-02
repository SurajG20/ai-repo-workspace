"use client";

import * as React from "react";
import { ScanSearch } from "lucide-react";
import { toast } from "sonner";

import { api, DeadCodeCandidate, DeadCodeResult, RepositoryItem } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const kindColor: Record<string, string> = {
  function: "text-chart-1 border-chart-1/40",
  class: "text-chart-4 border-chart-4/40",
  variable: "text-chart-3 border-chart-3/40",
};

export default function DeadCodePage() {
  const [repos, setRepos] = React.useState<RepositoryItem[]>([]);
  const [repoId, setRepoId] = React.useState("");
  const [result, setResult] = React.useState<DeadCodeResult | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    api
      .get<RepositoryItem[]>("/repositories")
      .then((r) => {
        setRepos(r);
        if (r.length) setRepoId(r[0].id);
      })
      .catch(() => {});
  }, []);

  const load = async () => {
    if (!repoId) return;
    setBusy(true);
    try {
      const res = await api.get<DeadCodeResult>(
        `/repositories/${repoId}/dead-code?min_refs=0`
      );
      setResult(res);
    } catch (e: any) {
      toast(e.message);
    } finally {
      setBusy(false);
    }
  };

  React.useEffect(() => {
    if (repoId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repoId]);

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 px-4 pt-4 lg:px-6">
      <div className="flex flex-wrap items-center gap-2">
        <div className="mr-auto">
          <h1 className="flex items-center gap-2 font-display text-xl font-semibold">
            <ScanSearch className="size-5 text-primary" />
            Dead code
          </h1>
          <p className="text-sm text-muted-foreground">
            Symbols with zero incoming references in the call graph.
          </p>
        </div>
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
        <Button size="sm" onClick={load} disabled={busy}>
          {busy ? "Scanning…" : "Scan"}
        </Button>
      </div>

      {busy ? (
        <Card>
          <CardContent className="flex flex-col gap-3 py-6">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-5/6" />
          </CardContent>
        </Card>
      ) : result ? (
        <>
          <div className="font-data text-xs text-muted-foreground">
            {result.count} candidate(s) — deterministic symbol-graph scan, no LLM.
          </div>
          <div className="overflow-hidden rounded-lg border">
            <div className="max-h-[60vh] overflow-auto">
              <table className="w-full text-left">
                <thead className="sticky top-0 bg-muted/60 backdrop-blur">
                  <tr className="font-data text-[10px] uppercase tracking-widest text-muted-foreground">
                    <th className="px-4 py-2 font-medium">symbol</th>
                    <th className="px-4 py-2 font-medium">kind</th>
                    <th className="px-4 py-2 font-medium">location</th>
                    <th className="px-4 py-2 text-right font-medium">outbound</th>
                    <th className="px-4 py-2 text-right font-medium">entry</th>
                  </tr>
                </thead>
                <tbody>
                  {result.candidates.map((c) => (
                    <DeadRow key={c.symbol_id} c={c} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <div className="flex flex-1 items-center justify-center rounded-lg border border-dashed py-16">
          <p className="font-data text-sm text-muted-foreground">
            Select a repository and scan.
          </p>
        </div>
      )}
    </div>
  );
}

function DeadRow({ c }: { c: DeadCodeCandidate }) {
  return (
    <tr className="border-t transition-colors hover:bg-muted/30">
      <td className="px-4 py-2">
        <div className="font-data text-xs">{c.name}</div>
        <div className="font-data text-[10px] text-muted-foreground">
          {c.parent_name ?? "—"}
        </div>
      </td>
      <td className="px-4 py-2">
        <Badge
          variant="outline"
          className={cn("font-data text-[10px]", kindColor[c.kind] ?? "")}
        >
          {c.kind}
        </Badge>
      </td>
      <td className="px-4 py-2">
        <div className="font-data text-[11px] text-muted-foreground">
          {c.file_path}:{c.start_line}
        </div>
        <div className="font-data text-[10px] text-muted-foreground/60">
          {c.signature ?? ""}
        </div>
      </td>
      <td className="px-4 py-2 text-right font-data text-xs tabular-nums">
        {c.outbound_links}
      </td>
      <td className="px-4 py-2 text-right">
        <Badge
          variant="outline"
          className={cn(
            "font-data text-[10px]",
            c.entry_point
              ? "text-chart-3 border-chart-3/40"
              : "text-muted-foreground"
          )}
        >
          {c.entry_point ? "entry" : "—"}
        </Badge>
      </td>
    </tr>
  );
}
