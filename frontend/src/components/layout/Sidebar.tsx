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
    <div className="w-64 bg-slate-900 h-screen text-slate-300 flex flex-col shrink-0">
      <div className="p-4 text-xl font-bold text-white border-b border-slate-800">
        SEO Setup
      </div>
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                "flex items-center space-x-3 px-3 py-2 rounded-md hover:bg-slate-800 transition-colors",
                isActive ? "bg-slate-800 text-white font-medium" : ""
              )
            }
          >
            <item.icon className="w-5 h-5" />
            <span>{item.name}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
