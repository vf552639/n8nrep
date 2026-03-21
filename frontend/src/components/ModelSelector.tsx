import { useState, useRef, useEffect } from "react";
import { ChevronDown, Search } from "lucide-react";

interface ModelSelectorProps {
  value: string;
  models: string[];
  onChange: (model: string) => void;
}

export function ModelSelector({ value, models, onChange }: ModelSelectorProps) {
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
    <div className="relative w-full" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between bg-white border border-slate-200 hover:border-blue-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-md px-3 py-1.5 text-sm text-slate-800 transition-colors shadow-sm"
      >
        <span className="truncate flex items-center gap-2">
          <span className="text-slate-400">🤖</span> {value || "Select a model..."}
        </span>
        <ChevronDown className="w-4 h-4 text-slate-400" />
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-64 flex flex-col overflow-hidden">
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
