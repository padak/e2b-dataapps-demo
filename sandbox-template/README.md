# Next.js Data App - E2B Sandbox Template

This is an E2B sandbox template for building data-driven Next.js applications with React, TypeScript, and Tailwind CSS.

## Features

- **Next.js 14.2.5** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** for styling with shadcn/ui theming
- **Radix UI** components for accessible UI primitives
- **Recharts** for data visualization
- **TanStack Table** for advanced table features
- **Zustand** for state management
- **Lucide React** for icons
- **date-fns** for date manipulation

## Template Structure

```
sandbox-template/
├── app/
│   ├── globals.css       # Global styles with shadcn theming
│   ├── layout.tsx        # Root layout
│   └── page.tsx          # Home page
├── components/
│   └── ui/
│       └── button.tsx    # shadcn Button component
├── lib/
│   └── utils.ts          # Utility functions (cn helper)
├── e2b.toml              # E2B configuration
├── Dockerfile            # Container configuration
├── package.json          # Dependencies
├── next.config.mjs       # Next.js configuration
├── tailwind.config.ts    # Tailwind configuration
├── tsconfig.json         # TypeScript configuration
└── postcss.config.mjs    # PostCSS configuration
```

## Building the Template

To build this E2B sandbox template:

```bash
e2b template build
```

This will:
1. Build the Docker image with all dependencies
2. Create an E2B sandbox template
3. Register it with the template ID: `nextjs-data-app`

## Using the Template

Once built, you can create sandboxes from this template:

```python
from e2b import Sandbox

# Create a sandbox from the template
sandbox = Sandbox(template="nextjs-data-app")

# The Next.js dev server will be running on port 3000
# You can access it via the sandbox's URL
```

## Development

The template includes:

- Hot module replacement (HMR) for fast development
- TypeScript for type checking
- ESLint for code quality
- Tailwind CSS with custom theme variables
- shadcn/ui compatible component structure

## Port Configuration

- **Port 3000**: Next.js development server

## Dependencies

All dependencies are pre-installed in the Docker image:
- Core: React 18, Next.js 14.2.5, TypeScript 5
- UI: Radix UI components, Tailwind CSS, shadcn/ui
- Data: Recharts, TanStack Table
- State: Zustand
- Utilities: date-fns, lucide-react, clsx, tailwind-merge
