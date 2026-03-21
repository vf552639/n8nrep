import { useCallback, useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import Sidebar, { readSidebarCollapsed, writeSidebarCollapsed } from "./Sidebar";
import Header from "./Header";

export default function MainLayout() {
  const { pathname } = useLocation();
  const isPromptsPage = pathname === "/prompts";

  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() =>
    typeof window !== "undefined" ? readSidebarCollapsed() : false
  );

  useEffect(() => {
    writeSidebarCollapsed(sidebarCollapsed);
  }, [sidebarCollapsed]);

  const onToggleSidebar = useCallback(() => {
    setSidebarCollapsed((c) => !c);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar collapsed={sidebarCollapsed} onToggleCollapsed={onToggleSidebar} />
      <div className="flex min-w-0 flex-1 flex-col transition-all duration-300 ease-in-out">
        {!isPromptsPage && <Header />}
        <main
          className={cn(
            "min-h-0 flex-1 overflow-auto",
            isPromptsPage ? "flex flex-col bg-slate-100 p-0" : "p-6"
          )}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
