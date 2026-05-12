import AccountChip from "@/components/AccountChip";

export default function Header() {
  return (
    <header className="h-16 border-b bg-white flex items-center justify-between px-6 shrink-0">
      <div className="text-lg font-semibold text-slate-800">SEO Content Generator UI</div>
      <AccountChip />
    </header>
  );
}
