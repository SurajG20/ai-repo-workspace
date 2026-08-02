"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Boxes,
  GitBranch,
  LayoutDashboard,
  MessageSquareText,
  ScanSearch,
  Settings2,
  Workflow,
} from "lucide-react";

import { RepoGraphMark, Wordmark } from "@/components/brand";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";

const groups = [
  {
    label: "Operate",
    items: [
      { title: "Dashboard", url: "/dashboard", icon: LayoutDashboard },
      { title: "Repositories", url: "/repositories", icon: Boxes },
      { title: "Explorer", url: "/explorer", icon: GitBranch },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { title: "Q&A", url: "/qa", icon: MessageSquareText },
      { title: "Dead Code", url: "/dead-code", icon: ScanSearch },
      { title: "Pipeline", url: "/pipeline", icon: Workflow },
    ],
  },
  {
    label: "System",
    items: [{ title: "Settings", url: "/settings", icon: Settings2 }],
  },
];

export function AppSidebar({
  className,
  ...props
}: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname();

  return (
    <Sidebar variant="inset" collapsible="icon" className={className} {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild size="lg">
              <Link href="/" className="gap-3">
                <RepoGraphMark className="size-7 text-primary" />
                <div className="flex flex-col leading-tight">
                  <Wordmark className="text-base" />
                  <span className="font-data text-[10px] uppercase tracking-widest text-muted-foreground">
                    repo intelligence
                  </span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        {groups.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => {
                  const active =
                    pathname === item.url || pathname.startsWith(item.url + "/");
                  return (
                    <SidebarMenuItem key={item.title}>
                      <SidebarMenuButton
                        asChild
                        isActive={active}
                        tooltip={item.title}
                      >
                        <Link href={item.url}>
                          <item.icon
                            className={cn(
                              active
                                ? "text-primary"
                                : "text-muted-foreground group-data-[collapsible=icon]:text-sidebar-foreground"
                            )}
                          />
                          <span>{item.title}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter>
        <div className="flex items-center gap-2 px-2 py-1">
          <span className="relative flex size-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
            <span className="relative inline-flex size-2 rounded-full bg-emerald-400" />
          </span>
          <span className="font-data text-xs text-muted-foreground">
            worker: online
          </span>
        </div>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
