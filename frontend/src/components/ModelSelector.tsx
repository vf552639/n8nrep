import { useState, useRef, useEffect } from "react";
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
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filtered = models.filter((m) =>
    m.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className={cn("relative w-full", className)} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full min-w-[220px] max-w-[260px] items-center justify-between rounded-lg border border-slate-300 bg-white px-3 py-[7px] text-left text-[13px] font-medium font-mono text-slate-800 shadow-inner transition-colors hover:border-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        <span className="min-w-0 flex-1 truncate">{value || "Select a model..."}</span>
        <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 flex max-h-64 w-full flex-col overflow-hidden rounded-xl border border-slate-300 bg-white shadow-xl">
          <div className="sticky top-0 bg-white border-b border-slate-100 p-2 shrink-0">
            <div className="relative">
              <Search className="absolute left-2.5 top-2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                autoFocus
                placeholder="Search models..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-sm border-none bg-slate-50 focus:bg-white rounded outline-none ring-1 ring-transparent focus:ring-blue-500"
              />
            </div>
          </div>
          <div className="overflow-y-auto flex-1 p-1">
            {filtered.length > 0 ? (
              filtered.map((m) => (
                <div
                  key={m}
                  onClick={() => {
                    onChange(m);
                    setIsOpen(false);
                    setSearch("");
                  }}
                  className={`px-3 py-2 text-sm rounded-md cursor-pointer transition-colors ${
                    value === m
                      ? "bg-blue-50 text-blue-700 font-medium"
                      : "text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {m}
                </div>
              ))
            ) : (
              <div className="p-3 text-center text-sm text-slate-500">
                No models found
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
