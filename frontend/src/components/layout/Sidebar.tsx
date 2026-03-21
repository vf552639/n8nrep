import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  CheckSquare,
  FileText,
  Globe,
  Users,
  MessageSquare,
  FileBox,
  FolderKanban,
  Settings,
  ScrollText,
  Wrench,
} from "lucide-react";

const navItems = [
  { name: "Dashboard", path: "/", icon: LayoutDashboard },
  { name: "Tasks", path: "/tasks", icon: CheckSquare },
  { name: "Articles", path: "/articles", icon: FileText },
  { name: "Sites", path: "/sites", icon: Globe },
  { name: "Authors", path: "/authors", icon: Users },
  { name: "Prompts", path: "/prompts", icon: MessageSquare },
  { name: "Blueprints", path: "/blueprints", icon: FileBox },
  { name: "Projects", path: "/projects", icon: FolderKanban },
  { name: "Settings", path: "/settings", icon: Settings },
  { name: "Logs", path: "/logs", icon: ScrollText },
];

export default function Sidebar() {
  return (
    <div className="flex h-screen w-64 shrink-0 flex-col bg-slate-900 text-slate-300">
      <div className="border-b border-slate-800 p-4 text-xl font-bold text-white">SEO Setup</div>
      <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto p-4">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                "flex items-center space-x-3 rounded-md px-3 py-2 transition-colors hover:bg-slate-800",
                isActive ? "bg-slate-800 font-medium text-white" : ""
              )
            }
          >
            <item.icon className="h-5 w-5 shrink-0" />
            <span>{item.name}</span>
          </NavLink>
        ))}
      </nav>
      <div className="shrink-0 border-t border-slate-800 p-2">
        <NavLink
          to="/seo-setup"
          className={({ isActive }) =>
            cn(
              "flex items-center space-x-3 rounded-md px-3 py-2.5 transition-colors hover:bg-slate-800",
              isActive ? "bg-slate-800 font-medium text-white" : ""
            )
          }
        >
          <Wrench className="h-5 w-5 shrink-0" />
          <span>SEO Setup</span>
        </NavLink>
      </div>
    </div>
  );
}
