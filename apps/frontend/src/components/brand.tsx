import { cn } from "@/lib/utils";

export function RepoGraphMark({
  className,
  animated = false,
}: {
  className?: string;
  animated?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      className={cn("h-8 w-8", className)}
      aria-hidden="true"
    >
      <rect x="1" y="1" width="30" height="30" rx="6" stroke="currentColor" strokeOpacity="0.25" strokeWidth="1.2" />
      <circle cx="9" cy="9" r="3" fill="hsl(var(--primary))" />
      <circle cx="23" cy="9" r="2" fill="hsl(var(--chart-2))" />
      <circle cx="16" cy="20" r="2.5" fill="hsl(var(--chart-3))" />
      <circle cx="24" cy="22" r="1.6" fill="currentColor" fillOpacity="0.4" />
      <path
        d="M9 9 L23 9 M23 9 L16 20 M9 9 L16 20 M16 20 L24 22"
        stroke="currentColor"
        strokeWidth="1"
        strokeOpacity="0.55"
        className={animated ? "origin-center" : ""}
      />
    </svg>
  );
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("font-display text-lg font-semibold tracking-tight", className)}>
      repograph
    </span>
  );
}
