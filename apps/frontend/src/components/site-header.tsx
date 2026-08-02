"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { KeyRound, Plus } from "lucide-react";

import { getToken, setToken } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";

export function SiteHeader() {
  const pathname = usePathname();
  const [token, setLocalToken] = React.useState("");

  const title = React.useMemo(() => {
    const seg = pathname.split("/").filter(Boolean);
    if (seg.length === 0) return "overview";
    return seg[seg.length - 1];
  }, [pathname]);

  const save = () => {
    if (token.trim()) {
      setToken(token.trim());
      toast("API token saved.");
    }
  };

  return (
    <header className="sticky top-0 z-10 flex h-12 shrink-0 items-center gap-2 border-b bg-background/80 backdrop-blur">
      <div className="flex w-full items-center gap-2 px-4 lg:px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="mx-2 h-4!" />
        <h1 className="font-data text-sm font-medium tracking-wide">{title}</h1>        <div className="ml-auto flex items-center gap-2">
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="ghost" size="sm" className="font-data text-xs">
                <KeyRound className="size-3.5" />
                {getToken() ? "API key" : "set API key"}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>API token</DialogTitle>
                <DialogDescription>
                  Paste a bearer token for the local API. In development, generate
                  one in the backend container via
                  <code className="mx-1 rounded bg-muted px-1 font-data text-[11px]">
                    create_access_token
                  </code>
                  .
                </DialogDescription>
              </DialogHeader>
              <Input
                value={token}
                onChange={(e) => setLocalToken(e.target.value)}
                placeholder="eyJhbGciOiJIUzI1NiIs..."
                className="font-data"
              />
              <DialogFooter>
                <Button onClick={save}>Save token</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Button size="sm" className="font-data text-xs" asChild>
            <a href="/repositories">
              <Plus className="size-3.5" />
              Add repository
            </a>
          </Button>
        </div>
      </div>
    </header>
  );
}
