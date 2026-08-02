"use client";

import * as React from "react";
import {
  Activity,
  Boxes,
  FileCode2,
  GitFork,
  TrendingUp,
} from "lucide-react";

import { api, OverviewStats } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function KpiCard({
  label,
  value,
  suffix,
  footer,
  hint,
  icon,
  loading,
}: {
  label: string;
  value?: string | number;
  suffix?: string;
  footer?: string;
  hint?: string;
  icon: React.ReactNode;
  loading?: boolean;
}) {
  return (
    <Card className="relative overflow-hidden">
      <div className="pointer-events-none absolute -right-6 -top-6 opacity-[0.07]">
        {icon}
      </div>
      <CardHeader>
        <CardDescription className="font-data text-[11px] uppercase tracking-widest">
          {label}
        </CardDescription>
        {loading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <CardTitle className="font-display text-2xl font-semibold tabular-nums md:text-3xl">
            {value}
            {suffix ? (
              <span className="ml-1 text-sm font-normal text-muted-foreground">
                {suffix}
              </span>
            ) : null}
          </CardTitle>
        )}
      </CardHeader>
      <CardFooter className="flex-col items-start gap-1.5 text-sm">
        <div className="font-data text-xs text-muted-foreground">{footer ?? "—"}</div>
        {hint ? <div className="text-muted-foreground">{hint}</div> : null}
      </CardFooter>
    </Card>
  );
}

export function SectionCards({ overview }: { overview: OverviewStats | null }) {
  const loading = overview === null;
  const active = overview?.repositories_active ?? 0;
  const total = overview?.repositories_total ?? 0;

  const cards = [
    {
      label: "Repositories",
      value: total,
      footer:
        active > 0
          ? `${active} active`
          : "no repositories indexed",
      hint: active > 0 ? `${active} ready for queries` : undefined,
      icon: <Boxes className="size-32 text-primary" />,
    },
    {
      label: "Symbols indexed",
      value: overview?.symbols_total,
      footer: overview?.symbols_by_kind
        ? Object.entries(overview.symbols_by_kind)
            .map(([k, v]) => `${k} ${v}`)
            .join(" · ")
        : undefined,
      hint: "AST-level structural map",
      icon: <GitFork className="size-32 text-primary" />,
    },
    {
      label: "Files parsed",
      value: overview?.files_total,
      footer: overview?.snapshots_total
        ? `${overview.snapshots_total} snapshot${overview.snapshots_total > 1 ? "s" : ""} taken`
        : undefined,
      icon: <FileCode2 className="size-32 text-primary" />,
    },
    {
      label: "Index jobs",
      value: overview?.jobs.completed ?? 0,
      footer:
        overview && overview.jobs.queued + overview.jobs.running > 0
          ? `${overview.jobs.queued + overview.jobs.running} in flight`
          : "queue idle",
      hint:
        overview && overview.jobs.failed > 0
          ? `${overview.jobs.failed} failed`
          : "all green",
      icon: <Activity className="size-32 text-primary" />,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 px-4 sm:grid-cols-2 lg:grid-cols-4 lg:px-6">
      {cards.map((c) => (
        <KpiCard key={c.label} {...c} loading={loading} />
      ))}
    </div>
  );
}

export function IndexingBadge() {
  return (
    <Badge variant="outline" className="gap-1.5">
      <TrendingUp className="size-3" />
      <span className={cn("tabular-nums")}>pipeline live</span>
    </Badge>
  );
}
