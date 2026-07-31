import { ProtectedRoute } from "@/components/layout/protected-route";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { CommandPalette } from "@/components/layout/command-palette";
import { CommandPaletteProvider } from "@/context/command-palette-context";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <CommandPaletteProvider>
        <div className="flex min-h-svh bg-background">
          <Sidebar className="no-print" />
          <div className="flex min-w-0 flex-1 flex-col">
            <Topbar className="no-print" />
            <main className="flex-1 overflow-y-auto p-4 lg:p-6 print:overflow-visible print:p-0">{children}</main>
          </div>
        </div>
        <CommandPalette />
      </CommandPaletteProvider>
    </ProtectedRoute>
  );
}