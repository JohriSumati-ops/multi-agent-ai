import type { Metadata } from "next";
import { Toaster } from "sonner";

import { QueryProvider } from "@/context/query-provider";
import { ThemeProvider } from "@/context/theme-provider";
import { AuthProvider } from "@/context/auth-context";
import { PreferencesProvider } from "@/context/preferences-context";
import { TooltipProvider } from "@/components/ui/tooltip";

import "./globals.css";

export const metadata: Metadata = {
  title: "Research Assistant Console",
  description:
    "Multi-Agent AI Research Assistant — retrieval, memory, orchestration, and reasoning in one console.",
};

const THEME_INIT_SCRIPT = `
(function () {
  try {
    var stored = window.localStorage.getItem("maara_theme");
    var theme = stored === "light" ? "light" : "dark";
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.style.colorScheme = theme;
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        {/* Runs before paint to avoid a light/dark flash on load. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body suppressHydrationWarning>
        <ThemeProvider>
          <QueryProvider>
            <AuthProvider>
              <PreferencesProvider>
                <TooltipProvider delayDuration={200}>{children}</TooltipProvider>
              </PreferencesProvider>
              <Toaster
                position="top-right"
                toastOptions={{
                  className: "font-sans",
                  style: {
                    background: "var(--surface-elevated)",
                    color: "var(--foreground)",
                    border: "1px solid var(--border)",
                  },
                }}
              />
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}