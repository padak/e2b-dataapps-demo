"""
E2B Next.js Template - Pre-configured sandbox for AI-powered app building.

This template pre-installs Next.js 14 with TypeScript, Tailwind CSS, and common
data visualization packages, enabling instant app preview.
"""

from e2b import Template

# Package versions
NEXTJS_VERSION = "14.2.5"
REACT_VERSION = "18"

# Pre-installed npm packages
NEXTJS_PACKAGES = [
    # Core
    f"next@{NEXTJS_VERSION}",
    f"react@^{REACT_VERSION}",
    f"react-dom@^{REACT_VERSION}",
    "typescript@^5",
    "@types/react@^18",
    "@types/react-dom@^18",
    "@types/node@^20",

    # Styling
    "tailwindcss@^3.4",
    "autoprefixer@^10",
    "postcss@^8",
    "class-variance-authority@^0.7",
    "clsx@^2.1",
    "tailwind-merge@^2.3",

    # UI Components (shadcn/ui dependencies)
    "@radix-ui/react-dialog@^1.0",
    "@radix-ui/react-dropdown-menu@^2.0",
    "@radix-ui/react-select@^2.0",
    "@radix-ui/react-tabs@^1.0",
    "@radix-ui/react-tooltip@^1.0",
    "@radix-ui/react-slot@^1.0",

    # Data Visualization
    "recharts@^2.12",
    "@tanstack/react-table@^8.17",

    # Data Processing
    "papaparse@^5.4",
    "date-fns@^3.6",

    # Icons & Animation
    "lucide-react@^0.378",
    "framer-motion@^11.2",

    # State Management
    "zustand@^4.5",
    "@tanstack/react-query@^5.40",
]

# Base Next.js project files
BASE_FILES = {
    "package.json": """{
  "name": "data-app",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  }
}""",

    "next.config.mjs": """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
""",

    "tsconfig.json": """{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{"name": "next"}],
    "paths": {"@/*": ["./*"]}
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
""",

    "tailwind.config.ts": """import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
""",

    "postcss.config.mjs": """/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};

export default config;
""",

    "app/globals.css": """@tailwind base;
@tailwind components;
@tailwind utilities;
""",

    "app/layout.tsx": """import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Data App",
  description: "Built with E2B App Builder",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
""",

    "app/page.tsx": """export default function Home() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Welcome to Data App
        </h1>
        <p className="text-gray-600">
          Your app will appear here after AI generates the code.
        </p>
      </div>
    </main>
  );
}
""",

    "lib/utils.ts": """import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
""",
}

# Build template using fnm (Fast Node Manager) - userspace installation
template = (
    Template()
    .from_image("e2bdev/base")
    # Install fnm (Fast Node Manager) - no root required
    .run_cmd("curl -fsSL https://fnm.vercel.app/install | bash")
    # Source fnm and install Node.js 20
    .run_cmd('export PATH="/home/user/.local/share/fnm:$PATH" && eval "$(fnm env)" && fnm install 20')
    # Create app directory
    .run_cmd("mkdir -p /home/user/app")
)

# Write base files
for filepath, content in BASE_FILES.items():
    # Create directory if needed
    if "/" in filepath:
        dir_path = "/home/user/app/" + "/".join(filepath.split("/")[:-1])
        template = template.run_cmd(f"mkdir -p {dir_path}")

    # Write file using heredoc
    template = template.run_cmd(
        f"cat > /home/user/app/{filepath} << 'EOFMARKER'\n{content}\nEOFMARKER"
    )

# Install npm packages (with fnm environment)
packages_str = " ".join(NEXTJS_PACKAGES)
template = template.run_cmd(
    f'export PATH="/home/user/.local/share/fnm:$PATH" && '
    f'eval "$(fnm env)" && '
    f'cd /home/user/app && npm install {packages_str}'
)

# Set environment variables for runtime
template = template.set_envs({
    "PATH": "/home/user/.local/share/fnm/aliases/default/bin:/home/user/.local/share/fnm:$PATH",
    "WORKDIR": "/home/user/app",
})
