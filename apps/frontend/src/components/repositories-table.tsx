"use client";

import * as React from "react";
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  ArrowUpDown,
  ChevronDown,
  MoreHorizontal,
  Plus,
  RefreshCcw,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { api, ApiError, RepositoryItem } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

const statusStyles: Record<string, string> = {
  indexing: "text-chart-3 border-chart-3/40",
  active: "text-chart-4 border-chart-4/40",
  failed: "text-destructive border-destructive/40",
};

function AddRepositoryDialog({ onAdded }: { onAdded: () => void }) {
  const [open, setOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [path, setPath] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  const submit = async () => {
    if (!name.trim() || !path.trim()) return;
    setBusy(true);
    try {
      await api.post<RepositoryItem>("/repositories", {
        name: name.trim(),
        local_path: path.trim(),
      });
      toast("Repository registered. Sync scheduled.");
      setOpen(false);
      setName("");
      setPath("");
      onAdded();
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to add repository", {
        style: { color: "hsl(var(--destructive))" },
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Plus className="size-4" />
          Add
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Register a repository</DialogTitle>
          <DialogDescription>
            Point Repograph at a local checkout. A snapshot + parse + graph-sync
            pipeline runs automatically.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="grid gap-2">
            <Label htmlFor="repo-name" className="font-data text-xs">
              name
            </Label>
            <Input
              id="repo-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my-service"
              className="font-data"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="repo-path" className="font-data text-xs">
              local path (in worker container)
            </Label>
            <Input
              id="repo-path"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="/app/workspace/apps/api"
              className="font-data"
            />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={submit} disabled={busy}>
            {busy ? "Registering…" : "Register"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RepositoriesTable() {
  const [repos, setRepos] = React.useState<RepositoryItem[] | null>(null);
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] =
    React.useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = React.useState({});

  const load = React.useCallback(() => {
    api
      .get<RepositoryItem[]>("/repositories")
      .then(setRepos)
      .catch((e) => toast(e.message, { style: { color: "hsl(var(--destructive))" } }));
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  const sync = async (id: string) => {
    try {
      const res = await api.post<{ status: string; message: string }>(
        `/repositories/${id}/sync`
      );
      toast(res.message || "Sync triggered.");
      setTimeout(load, 2500);
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Sync failed");
    }
  };

  const remove = async (id: string) => {
    try {
      await api.del(`/repositories/${id}`);
      toast("Repository removed.");
      load();
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Delete failed");
    }
  };

  const columns: ColumnDef<RepositoryItem>[] = React.useMemo(
    () => [
      {
        id: "select",
        header: ({ table }) => (
          <Checkbox
            checked={
              table.getIsAllPageRowsSelected() ||
              (table.getIsSomePageRowsSelected() && "indeterminate")
            }
            onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
            aria-label="Select all"
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(value) => row.toggleSelected(!!value)}
            aria-label="Select row"
          />
        ),
        enableSorting: false,
        enableHiding: false,
      },
      {
        accessorKey: "full_name",
        header: ({ column }) => (
          <Button
            variant="ghost"
            className="-ml-3 h-8 px-2 font-data text-xs"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            name
            <ArrowUpDown className="size-3" />
          </Button>
        ),
        cell: ({ row }) => (
          <div className="flex flex-col gap-0.5">
            <span className="font-data text-sm">{row.getValue("full_name")}</span>
            <span className="text-xs text-muted-foreground">
              {row.original.provider}
              {row.original.default_branch
                ? ` · ${row.original.default_branch}`
                : ""}
            </span>
          </div>
        ),
      },
      {
        accessorKey: "status",
        header: () => (
          <span className="font-data text-xs">status</span>
        ),
        cell: ({ row }) => (
          <Badge
            variant="outline"
            className={cn(
              "font-data text-xs",
              statusStyles[row.getValue<string>("status")] ?? "text-muted-foreground"
            )}
          >
            {row.getValue("status")}
          </Badge>
        ),
      },
      {
        accessorKey: "language",
        header: () => <span className="font-data text-xs">language</span>,
        cell: ({ row }) => (
          <span className="font-data text-xs text-muted-foreground">
            {row.getValue("language") ?? "—"}
          </span>
        ),
      },
      {
        accessorKey: "size_bytes",
        header: () => <span className="font-data text-xs">size</span>,
        cell: ({ row }) => (
          <span className="font-data text-xs tabular-nums">
            {row.getValue<number>("size_bytes") > 0
              ? `${(row.getValue<number>("size_bytes") / 1024).toFixed(0)} KB`
              : "—"}
          </span>
        ),
      },
      {
        accessorKey: "last_synced_at",
        header: ({ column }) => (
          <Button
            variant="ghost"
            className="-ml-3 h-8 px-2 font-data text-xs"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            last sync
            <ArrowUpDown className="size-3" />
          </Button>
        ),
        cell: ({ row }) => {
          const v = row.getValue<string | null>("last_synced_at");
          return (
            <span className="font-data text-xs text-muted-foreground">
              {v ? new Date(v).toLocaleString() : "never"}
            </span>
          );
        },
      },
      {
        id: "actions",
        enableHiding: false,
        cell: ({ row }) => (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0">
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel className="font-data text-xs">
                {row.original.full_name}
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => sync(row.original.id)}
                className="gap-2"
              >
                <RefreshCcw className="size-4" />
                Re-index
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => remove(row.original.id)}
                className="gap-2 text-destructive focus:text-destructive"
              >
                <Trash2 className="size-4" />
                Remove
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ),
      },
    ],
    []
  );

  const table = useReactTable({
    data: repos ?? [],
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
    },
  });

  return (
    <div className="w-full px-4 lg:px-6">
      <div className="flex flex-col gap-4 py-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="font-display text-base font-semibold">Repositories</h2>
          <p className="text-sm text-muted-foreground">
            Registered sources and their index state.
          </p>
        </div>
        <div className="flex flex-1 items-center gap-2 md:justify-end">
          <Input
            placeholder="Filter by name…"
            value={(table.getColumn("full_name")?.getFilterValue() as string) ?? ""}
            onChange={(event) =>
              table.getColumn("full_name")?.setFilterValue(event.target.value)
            }
            className="h-8 w-full font-data text-xs md:max-w-xs"
          />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                Columns <ChevronDown className="size-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {table
                .getAllColumns()
                .filter((column) => column.getCanHide())
                .map((column) => (
                  <DropdownMenuCheckboxItem
                    key={column.id}
                    className="capitalize"
                    checked={column.getIsVisible()}
                    onCheckedChange={(value) =>
                      column.toggleVisibility(!!value)
                    }
                  >
                    {column.id.replaceAll("_", " ")}
                  </DropdownMenuCheckboxItem>
                ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <AddRepositoryDialog onAdded={load} />
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {repos === null ? (
              <TableRow>
                {Array.from({ length: 7 }).map((_, i) => (
                  <TableCell key={i} className="py-3">
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                ))}
              </TableRow>
            ) : table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="py-2.5">
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center font-data text-sm text-muted-foreground"
                >
                  No repositories registered. Add one to begin indexing.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between px-2 py-4">
        <div className="font-data text-xs text-muted-foreground">
          {table.getFilteredSelectedRowModel().rows.length} of{" "}
          {table.getFilteredRowModel().rows.length} row(s) selected
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={`${table.getState().pagination.pageSize}`}
            onValueChange={(value) => table.setPageSize(Number(value))}
          >
            <SelectTrigger className="h-8 w-16 font-data text-xs">
              <SelectValue placeholder={table.getState().pagination.pageSize} />
            </SelectTrigger>
            <SelectContent side="top">
              {[5, 10, 20].map((size) => (
                <SelectItem key={size} value={`${size}`} className="font-data text-xs">
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              Prev
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              Next
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
