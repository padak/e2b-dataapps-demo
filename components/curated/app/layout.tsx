import "./globals.css";

export const metadata = {
  title: "Curated Components Demo",
  description: "Preview of curated UI components",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">{children}</body>
    </html>
  );
}
