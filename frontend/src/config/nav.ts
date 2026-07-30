import {
  LayoutDashboard,
  FileText,
  Search,
  BrainCircuit,
  Workflow,
  Sparkles,
  Activity,
  BarChart3,
  Settings,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Documents", href: "/documents", icon: FileText },
  { label: "Retrieval", href: "/retrieval", icon: Search },
  { label: "Memory", href: "/memory", icon: BrainCircuit },
  { label: "Orchestration", href: "/orchestration", icon: Workflow },
  { label: "Research", href: "/research", icon: Sparkles },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "System", href: "/system", icon: Activity },
  { label: "Settings", href: "/settings", icon: Settings },
];
