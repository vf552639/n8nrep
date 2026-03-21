import { Outlet, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import Sidebar from "./Sidebar";
import Header from "./Header";

export default function MainLayout() {
  const { pathname } = useLocation();
  const isPromptsPage = pathname === "/prompts";

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 min-w-0 flex-col">
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
