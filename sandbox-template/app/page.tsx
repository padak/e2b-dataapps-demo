import { Button } from "@/components/ui/button"

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-center font-mono text-sm flex flex-col gap-8">
        <h1 className="text-4xl font-bold text-center">
          App Builder Ready
        </h1>
        <p className="text-muted-foreground text-center max-w-md">
          This Next.js data application template is ready for development.
          Start building your data-driven applications with React, TypeScript, and Tailwind CSS.
        </p>
        <div className="flex gap-4">
          <Button>Get Started</Button>
          <Button variant="outline">Learn More</Button>
        </div>
      </div>
    </main>
  )
}
