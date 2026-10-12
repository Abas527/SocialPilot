import { Code2, Heart, MoveUpRight } from 'lucide-react'

type FooterProps = {
  onOpenWorkspace: () => void
}

export function Footer({ onOpenWorkspace }: FooterProps) {
  return (
    <footer className="border-t border-white/[0.08] bg-[#070a13]">
      <div className="mx-auto flex max-w-7xl flex-col gap-7 px-5 py-8 sm:px-8 md:flex-row md:items-center md:justify-between lg:px-10">
        <a href="#top" className="inline-flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg border border-indigo-300/20 bg-indigo-400/10 font-display text-[11px] font-bold text-indigo-100">SP</span>
          <span className="font-display text-sm font-semibold tracking-tight text-white">SocialPilot <span className="text-indigo-300">AI</span></span>
        </a>
        <p className="max-w-sm text-xs leading-5 text-slate-500">A project in progress: helping developers share the work behind the code.</p>
        <div className="flex items-center gap-5 text-xs text-slate-400">
          <button onClick={onOpenWorkspace} className="transition-colors hover:text-white">Open workspace <MoveUpRight className="ml-1 inline" size={12} /></button>
          <a href="#vision" className="transition-colors hover:text-white">Our vision</a>
          <a href="#top" className="transition-colors hover:text-white" aria-label="Back to top">Back to top ↑</a>
        </div>
      </div>
      <div className="border-t border-white/[0.05]">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 text-[10px] text-slate-600 sm:px-8 lg:px-10">
          <span>© 2026 SocialPilot AI · Early-stage concept and MVP</span>
          <span className="inline-flex items-center gap-1.5"><Code2 size={12} /> Built for people who build <Heart size={11} className="text-indigo-400" /></span>
        </div>
      </div>
    </footer>
  )
}
