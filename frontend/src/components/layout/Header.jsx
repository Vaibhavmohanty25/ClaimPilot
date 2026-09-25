import { Bell } from "lucide-react";

function Header() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6 lg:px-8">
      <div>
        <p className="text-sm text-slate-500">
          Human-in-the-loop claims investigation
        </p>
      </div>

      <div className="flex items-center gap-4">
        <button
          type="button"
          className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"
        >
          <Bell size={19} />
        </button>

        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
          CP
        </div>
      </div>
    </header>
  );
}

export default Header;