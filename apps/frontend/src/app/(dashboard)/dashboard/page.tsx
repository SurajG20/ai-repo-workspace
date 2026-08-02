"use client";

import * as React from "react";
import { AlertTriangle } from "lucide-react";

import { api, OverviewStats, RepositoryItem } from "@/lib/api";
import { SectionCards } from "@/components/section-cards";
import { ChartAreaInteractive } from "@/components/chart-area-interactive";
import { RepositoriesTable } from "@/components/repositories-table";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export default function DashboardPage() {
  const [overview, setOverview] = React.useState<OverviewStats | null>(null);
  const [repos, setRepos] = React.useState<RepositoryItem[] | null>(null);
  const [authError, setAuthError] = React.useState(false);

  React.useEffect(() => {
    api
      .get<OverviewStats>("/repositories/stats/overview")
      .then(setOverview)
      .catch((e) => {
        if (e.status === 401) setAuthError(true);
      });
    api
      .get<RepositoryItem[]>("/repositories")
      .then(setRepos)
      .catch(() => {});
  }, []);

  const repoId = repos?.[0]?.id;

  return (
    <>
      {authError ? (
        <div className="px-4 pt-4 lg:px-6">
          <Alert>
            <AlertTriangle className="size-4" />
            <AlertTitle>API requires authentication</AlertTitle>
            <AlertDescription>
              Set your bearer token via the &quot;API key&quot; button in the
              header to load live data.
            </AlertDescription>
          </Alert>
        </div>
      ) : null}
      <SectionCards overview={overview} />
      <div className="px-4 lg:px-6">
        <ChartAreaInteractive repositoryId={repoId} />
      </div>
      <RepositoriesTable />
    </>
  );
}
