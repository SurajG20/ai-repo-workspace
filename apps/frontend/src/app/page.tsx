export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold tracking-tight">
        AI Repository Workspace
      </h1>
      <p className="mt-4 text-lg text-muted-foreground">
        An AI operating system for repositories.
      </p>
      <div className="mt-8 flex gap-4">
        <a
          href="http://localhost:8000/docs"
          className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent"
        >
          API Docs
        </a>
        <a
          href="http://localhost:8000/health"
          className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent"
        >
          Health Check
        </a>
      </div>
    </main>
  );
}
