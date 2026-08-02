"use client";

import * as React from "react";
import { Send, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { api, AskResult, RepositoryItem, SearchHit } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

const kindColor: Record<string, string> = {
  function: "text-chart-1 border-chart-1/40",
  class: "text-chart-4 border-chart-4/40",
  variable: "text-chart-3 border-chart-3/40",
  module: "text-chart-5 border-chart-5/40",
};

export default function QaPage() {
  const [repos, setRepos] = React.useState<RepositoryItem[]>([]);
  const [repoId, setRepoId] = React.useState<string>("");
  const [question, setQuestion] = React.useState("");
  const [result, setResult] = React.useState<AskResult | null>(null);
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

  const ask = async () => {
    if (!repoId || !question.trim()) return;
    setBusy(true);
    try {
      const res = await api.post<AskResult>(`/repositories/${repoId}/ask`, {
        question: question.trim(),
      });
      setResult(res);
    } catch (e: any) {
      toast(e.message);
    } finally {
      setBusy(false);
    }
  };

  const llmError = result?.retrieval.llm?.error;

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-4 px-4 pt-4 lg:px-6">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-xl font-semibold">Repository Q&A</h1>
        <p className="text-sm text-muted-foreground">
          Graph-grounded answers over the symbol graph and codebase — every claim
          is cited to a file, line and symbol.
        </p>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <Select value={repoId} onValueChange={setRepoId}>
          <SelectTrigger className="h-9 w-full font-data text-xs sm:w-56">
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
        <div className="flex flex-1 gap-2">
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
            placeholder="e.g. how does create_access_token work?"
            className="h-9 flex-1 font-data text-xs"
          />
          <Button
            onClick={ask}
            disabled={busy || !question.trim() || !repoId}
            className="h-9"
          >
            <Send className="size-3.5" />
            {busy ? "Asking…" : "Ask"}
          </Button>
        </div>
      </div>

      {busy ? (
        <Card>
          <CardContent className="flex flex-col gap-3 py-6">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-2/3" />
          </CardContent>
        </Card>
      ) : result ? (
        <>
          <Card>
            <CardHeader className="flex flex-row items-start justify-between gap-4">
              <div>
                <CardTitle className="flex items-center gap-2 font-display text-base">
                  <Sparkles className="size-4 text-primary" />
                  Answer
                </CardTitle>
                <CardDescription className="font-data text-xs">
                  model {result.answer.model} · provider {result.answer.provider}
                </CardDescription>
              </div>
              {llmError ? (
                <Badge variant="outline" className="font-data text-xs">
                  retrieval-only
                </Badge>
              ) : null}
            </CardHeader>
            <CardContent className="whitespace-pre-wrap font-data text-sm leading-relaxed">
              {result.answer.answer}
            </CardContent>
          </Card>

          {result.answer.context_blocks.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="font-display text-base">Context blocks</CardTitle>
                <CardDescription>
                  Deterministic evidence used to ground the answer.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-2">
                {result.answer.context_blocks.map((b) => (
                  <div
                    key={`${b.file_path}:${b.start_line}`}
                    className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2"
                  >
                    <Badge
                      variant="outline"
                      className={`font-data text-xs ${kindColor[b.kind] ?? ""}`}
                    >
                      {b.kind}
                    </Badge>
                    <span className="font-data text-xs">{b.name}</span>
                    <span className="font-data text-xs text-muted-foreground">
                      {b.file_path}:{b.start_line}
                      {b.signature ? ` ${b.signature}` : ""}
                    </span>
                    <span className="ml-auto font-data text-xs text-muted-foreground">
                      {b.score.toFixed(3)}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle className="font-display text-base">
                Retrieved symbols
              </CardTitle>
              <CardDescription>
                Raw hybrid retrieval results (vector + symbol + keyword + graph).
              </CardDescription>
            </CardHeader>
            <CardContent>
              {result.retrieval.hits.length === 0 ? (
                <div className="font-data text-xs text-muted-foreground">
                  no hits
                </div>
              ) : (
                <div className="grid gap-2">
                  {result.retrieval.hits.map((h) => (
                    <SymbolRow key={h.symbol_id} hit={h} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : (
        <div className="flex flex-1 items-center justify-center rounded-lg border border-dashed py-16">
          <div className="text-center">
            <p className="font-data text-sm text-muted-foreground">
              Ask a question about a repository.
            </p>
            <p className="mt-1 font-data text-xs text-muted-foreground/70">
              without an LLM provider configured, you get deterministic
              retrieval-only answers
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function SymbolRow({ hit }: { hit: SearchHit }) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2">
      <Badge variant="outline" className={`font-data text-xs ${kindColor[hit.kind] ?? ""}`}>
        {hit.kind}
      </Badge>
      <span className="font-data text-xs">{hit.name}</span>
      <span className="font-data text-xs text-muted-foreground">
        {hit.file_path}:{hit.start_line}
        {hit.signature ? ` ${hit.signature}` : ""}
      </span>
      <div className="ml-auto flex items-center gap-2">
        {hit.sources.map((s) => (
          <Badge key={s} variant="secondary" className="font-data text-[10px]">
            {s}
          </Badge>
        ))}
        <span className="font-data text-xs text-muted-foreground">
          {hit.score.toFixed(3)}
        </span>
      </div>
    </div>
  );
}
