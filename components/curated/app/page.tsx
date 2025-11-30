import { KeboolaDataSection } from "./KeboolaDataSection"

export default function DemoPage() {
  return (
    <main className="min-h-screen bg-background">
      <div className="container py-8 max-w-7xl mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Curated Components</h1>
          <p className="text-muted-foreground mt-2">
            Pre-built UI components for data applications with shadcn/ui
          </p>
        </div>

        <section className="rounded-lg border bg-card p-6 shadow-sm">
          <h2 className="text-xl font-semibold mb-6">DataTable Component</h2>
          <KeboolaDataSection />
        </section>

        <section className="mt-8 rounded-lg border bg-card p-6 shadow-sm">
          <h2 className="text-xl font-semibold mb-4">Features</h2>
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              Auto-generated columns from data
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              Global search/filter
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              Column sorting
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              Column visibility toggle
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              Pagination
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              Loading skeleton
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              Built with shadcn/ui + TanStack Table
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              Keboola Query Service integration
            </li>
          </ul>
        </section>
      </div>
    </main>
  )
}
