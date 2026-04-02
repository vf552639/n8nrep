import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  CheckSquare,
  FileText,
  Globe,
  Building2,
  Users,
  MessageSquare,
  FileBox,
  FolderKanban,
  Settings,
  ScrollText,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const navItems = [
  { name: "Dashboard", path: "/", icon: LayoutDashboard },
  { name: "Tasks", path: "/tasks", icon: CheckSquare },
  { name: "Articles", path: "/articles", icon: FileText },
  { name: "Templates", path: "/templates", icon: Globe },
  { name: "Sites", path: "/sites", icon: Building2 },
  { name: "Legal Pages", path: "/legal-pages", icon: ScrollText },
  { name: "Authors", path: "/authors", icon: Users },
  { name: "Prompts", path: "/prompts", icon: MessageSquare },
  { name: "Blueprints", path: "/blueprints", icon: FileBox },
  { name: "Projects", path: "/projects", icon: FolderKanban },
  { name: "Settings", path: "/settings", icon: Settings },
  { name: "Logs", path: "/logs", icon: ScrollText },
];

const STORAGE_KEY = "sidebar_collapsed";

export function readSidebarCollapsed(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function writeSidebarCollapsed(collapsed: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, collapsed ? "true" : "false");
  } catch {
    /* ignore */
  }
}

type SidebarProps = {
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

export default function Sidebar({ collapsed, onToggleCollapsed }: SidebarProps) {
  return (
    <div
      className={cn(
        "flex h-screen shrink-0 flex-col overflow-hidden bg-slate-900 text-slate-300 transition-all duration-300 ease-in-out",
        collapsed ? "w-[72px]" : "w-56"
      )}
    >
      <div
        className={cn(
          "flex shrink-0 items-center border-b border-slate-800",
          collapsed ? "flex-col gap-2 px-2 py-3" : "justify-between gap-2 px-3 py-3"
        )}
      >
        {!collapsed && <div className="min-w-0 truncate text-lg font-bold text-white">SEO Content</div>}
        <button
          type="button"
          onClick={onToggleCollapsed}
          className={cn(
            "flex shrink-0 items-center justify-center rounded-md border border-slate-700 bg-slate-800/80 p-1.5 text-slate-300 transition-colors hover:bg-slate-800 hover:text-white",
            collapsed && "w-full"
          )}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            title={item.name}
            className={({ isActive }) =>
              cn(
                "flex items-center rounded-md py-2 transition-colors hover:bg-slate-800",
                collapsed ? "justify-center px-0" : "space-x-3 px-3",
                isActive ? "bg-slate-800 font-medium text-white" : ""
              )
            }
          >
            <item.icon className="h-5 w-5 shrink-0" />
            {!collapsed && <span>{item.name}</span>}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
