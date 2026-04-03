import { useState, useRef, useEffect, useLayoutEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, Search } from "lucide-react";
import { cn } from "@/lib/utils";

interface ModelSelectorProps {
  value: string;
  models: string[];
  onChange: (model: string) => void;
  /** Override width; default full width of parent */
  className?: string;
}

export function ModelSelector({ value, models, onChange, className }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0, width: 0 });

  const updatePosition = useCallback(() => {
    if (!buttonRef.current || !isOpen) return;
    const r = buttonRef.current.getBoundingClientRect();
    setMenuPos({ top: r.bottom + 4, left: r.left, width: r.width });
  }, [isOpen]);

  useLayoutEffect(() => {
    updatePosition();
  }, [isOpen, updatePosition]);

  useEffect(() => {
    if (!isOpen) return;
    updatePosition();
    window.addEventListener("scroll", updatePosition, true);
    window.addEventListener("resize", updatePosition);
    return () => {
      window.removeEventListener("scroll", updatePosition, true);
      window.removeEventListener("resize", updatePosition);
    };
  }, [isOpen, updatePosition]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const t = event.target as Node;
      if (buttonRef.current?.contains(t)) return;
      if (menuRef.current?.contains(t)) return;
      setIsOpen(false);
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  const filtered = models.filter((m) => m.toLowerCase().includes(search.toLowerCase()));

  const menu =
    isOpen &&
    createPortal(
      <div
        ref={menuRef}
        className="flex max-h-64 flex-col overflow-hidden rounded-xl border border-slate-300 bg-white shadow-xl"
        style={{
          position: "fixed",
          top: menuPos.top,
          left: menuPos.left,
          width: Math.max(menuPos.width, 220),
          zIndex: 100,
        }}
      >
        <div className="sticky top-0 shrink-0 border-b border-slate-100 bg-white p-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              autoFocus
              placeholder="Search models..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded border-none bg-slate-50 py-1.5 pl-8 pr-3 text-sm outline-none ring-1 ring-transparent focus:bg-white focus:ring-blue-500"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-1">
          {filtered.length > 0 ? (
            filtered.map((m) => (
              <div
                key={m}
                role="option"
                tabIndex={0}
                onClick={() => {
                  onChange(m);
                  setIsOpen(false);
                  setSearch("");
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onChange(m);
                    setIsOpen(false);
                    setSearch("");
                  }
                }}
                className={`cursor-pointer rounded-md px-3 py-2 text-sm transition-colors ${
                  value === m ? "bg-blue-50 font-medium text-blue-700" : "text-slate-700 hover:bg-slate-50"
                }`}
              >
                {m}
              </div>
            ))
          ) : (
            <div className="p-3 text-center text-sm text-slate-500">No models found</div>
          )}
        </div>
      </div>,
      document.body
    );

  return (
    <div className={cn("relative w-full shrink-0", className)}>
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full min-w-[220px] max-w-[260px] items-center justify-between rounded-lg border border-slate-300 bg-white px-3 py-[7px] text-left text-[13px] font-medium font-mono text-slate-800 shadow-inner transition-colors hover:border-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        <span className="min-w-0 flex-1 truncate">{value || "Select a model..."}</span>
        <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
      </button>
      {menu}
    </div>
  );
}
