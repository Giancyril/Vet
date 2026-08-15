import Link from "next/link";
import { Bot, GitPullRequest, LayoutDashboard, Settings, ShieldCheck } from "lucide-react";

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-border/80 bg-background/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5 font-semibold text-white tracking-tight">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-purple-500/20">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <span className="text-base font-bold bg-gradient-to-r from-white via-gray-100 to-gray-400 bg-clip-text text-transparent">
              Warden AI Reviewer
            </span>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20">
              v1.0
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            <Link
              href="/"
              className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium text-gray-200 hover:text-white hover:bg-surface-raised transition-colors"
            >
              <LayoutDashboard className="w-4 h-4 text-purple-400" />
              Reviews
            </Link>
            <Link
              href="/repos"
              className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium text-gray-400 hover:text-white hover:bg-surface-raised transition-colors"
            >
              <GitPullRequest className="w-4 h-4 text-gray-400" />
              Repositories
            </Link>
            <Link
              href="/config"
              className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium text-gray-400 hover:text-white hover:bg-surface-raised transition-colors"
            >
              <Settings className="w-4 h-4 text-gray-400" />
              Settings
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Webhook Guard Active
          </div>
        </div>
      </div>
    </header>
  );
}
