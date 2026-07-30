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
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col">
            <Topbar />
            <main className="flex-1 overflow-y-auto p-4 lg:p-6">{children}</main>
          </div>
        </div>
        <CommandPalette />
      </CommandPaletteProvider>
    </ProtectedRoute>
  );
}