import { ArrowRight, Code2, Sparkles } from 'lucide-react'

type FinalCTAProps = {
  onOpenWorkspace: () => void
}

export function FinalCTA({ onOpenWorkspace }: FinalCTAProps) {
  return (
    <section id="discover" className="scroll-mt-24 px-5 py-20 sm:px-8 lg:px-10 lg:py-28">
      <div className="relative mx-auto max-w-7xl overflow-hidden rounded-3xl border border-indigo-200/15 bg-[#10172a] px-6 py-12 sm:px-12 sm:py-16 lg:px-16">
        <div className="pointer-events-none absolute -right-16 -top-40 h-[420px] w-[420px] rounded-full border border-indigo-200/[0.07]" />
        <div className="pointer-events-none absolute -right-4 -top-28 h-[330px] w-[330px] rounded-full border border-cyan-200/[0.06]" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_80%_15%,rgba(99,102,241,.18),transparent_48%)]" />
        <div className="relative max-w-2xl">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-indigo-200/15 bg-indigo-200/[0.07] px-3 py-1.5 text-[10px] font-medium text-indigo-100"><Sparkles size={12} /> Build · Share · Grow</div>
          <h2 className="text-balance font-display text-3xl font-semibold leading-tight tracking-[-.045em] text-white sm:text-4xl lg:text-[48px]">Build something. Share what you learn. Grow with the community.</h2>
          <p className="mt-5 max-w-xl text-sm leading-6 text-slate-400">SocialPilot AI brings AI-assisted technical storytelling, developer networking, and direct creator support into one experience.</p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <button onClick={onOpenWorkspace} className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-indigo-500 px-5 text-xs font-semibold text-white transition-colors hover:bg-indigo-400"><Code2 size={14} /> Discover SocialPilot AI <ArrowRight size={14} /></button>
            <a href="#mvp" className="inline-flex h-11 items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-5 text-xs font-semibold text-slate-200 transition-colors hover:bg-white/[0.07]">Explore the MVP <ArrowRight size={14} /></a>
          </div>
          <p className="mt-5 text-[9px] text-slate-600">Early-stage project · illustrative product previews · no user or earnings claims</p>
        </div>
      </div>
    </section>
  )
}
