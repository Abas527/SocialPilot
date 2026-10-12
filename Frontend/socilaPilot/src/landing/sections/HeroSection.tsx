import { ArrowDown, ArrowRight, ArrowUpRight, BadgeCheck, BookOpenText, Blocks, Code2, Heart, Layers3, Sparkles } from 'lucide-react'

type HeroSectionProps = {
  onOpenWorkspace: () => void
}

export function HeroSection({ onOpenWorkspace }: HeroSectionProps) {
  return (
    <section id="top" className="relative isolate overflow-hidden border-b border-white/[0.06]">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_72%_38%,rgba(70,78,210,.19),transparent_38%),radial-gradient(ellipse_at_25%_4%,rgba(14,165,233,.10),transparent_34%)]" />
      <div className="pointer-events-none absolute right-[18%] top-24 -z-10 h-72 w-72 rounded-full border border-indigo-300/[0.06]" />
      <div className="mx-auto grid min-h-[680px] max-w-7xl items-center gap-12 px-5 pb-16 pt-14 sm:px-8 md:pt-20 lg:grid-cols-[.95fr_1.05fr] lg:gap-10 lg:px-10 lg:pb-24 lg:pt-20">
        <div className="max-w-xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-cyan-300/15 bg-cyan-300/[0.06] px-3 py-1.5 text-[11px] font-medium text-cyan-100/90">
            <Sparkles size={13} className="text-cyan-300" /> A new home for work worth sharing
          </div>
          <h1 className="max-w-[650px] text-balance font-display text-[43px] font-semibold leading-[1.08] tracking-[-0.055em] text-white sm:text-6xl lg:text-[66px]">
            Your Work Deserves More Than a <span className="bg-gradient-to-r from-cyan-200 via-blue-300 to-violet-300 bg-clip-text text-transparent">Repository.</span>
          </h1>
          <p className="mt-6 max-w-[560px] text-base leading-7 text-slate-400 sm:text-lg sm:leading-8">
            SocialPilot AI helps developers turn projects into compelling technical stories, build their professional presence, and receive direct support from the community that values their work.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <a href="#vision" className="inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-indigo-500 px-5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/50 transition-all hover:-translate-y-0.5 hover:bg-indigo-400">
              Explore the vision <ArrowRight size={16} />
            </a>
            <a href="#how-it-works" className="inline-flex h-12 items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-5 text-sm font-semibold text-slate-200 transition-all hover:border-white/20 hover:bg-white/[0.06]">
              How it works <ArrowDown size={15} />
            </a>
            <button onClick={onOpenWorkspace} className="inline-flex h-12 items-center justify-center gap-2 rounded-lg px-3 text-sm font-medium text-slate-400 transition-colors hover:text-white">
              Try the project studio <ArrowUpRight size={14} />
            </button>
          </div>
          <div className="mt-9 flex flex-wrap items-center gap-x-5 gap-y-2 text-[11px] text-slate-500">
            <span className="inline-flex items-center gap-1.5"><Code2 size={13} className="text-indigo-300" /> Real project context</span>
            <span className="h-1 w-1 rounded-full bg-slate-700" />
            <span className="inline-flex items-center gap-1.5"><BookOpenText size={13} className="text-indigo-300" /> Developer-first</span>
            <span className="h-1 w-1 rounded-full bg-slate-700" />
            <span className="inline-flex items-center gap-1.5"><Blocks size={13} className="text-cyan-200" /> Blockchain tips + purchases</span>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-[590px] lg:ml-auto">
          <div className="pointer-events-none absolute -inset-8 rounded-[40px] bg-indigo-500/[0.09] blur-3xl" />
          <div className="relative rounded-2xl border border-white/[0.12] bg-[#0d1323]/90 p-3 shadow-[0_32px_100px_-35px_rgba(4,5,20,.9)] backdrop-blur">
            <div className="flex items-center justify-between border-b border-white/[0.07] px-3 pb-3 pt-1">
              <div className="flex items-center gap-2"><span className="flex gap-1"><i className="h-2 w-2 rounded-full bg-rose-400/80" /><i className="h-2 w-2 rounded-full bg-amber-300/80" /><i className="h-2 w-2 rounded-full bg-emerald-300/80" /></span><span className="ml-2 text-[10px] text-slate-500">socialpilot.ai / project-story</span></div>
              <span className="rounded-full border border-indigo-300/15 bg-indigo-300/[0.07] px-2 py-1 text-[8px] font-semibold uppercase tracking-wider text-indigo-200">Illustrative preview</span>
            </div>
            <div className="grid gap-3 p-2 sm:grid-cols-[.88fr_1.12fr]">
              <div className="space-y-3">
                <div className="rounded-xl border border-white/[0.08] bg-[#111a2d] p-3.5">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold text-slate-200"><Code2 size={12} className="text-cyan-300" /> Project source</span>
                    <span className="text-[9px] text-slate-500">01 / 04</span>
                  </div>
                  <div className="rounded-lg border border-white/[0.06] bg-[#0a1020] p-3">
                    <div className="flex items-center gap-2"><span className="grid h-7 w-7 place-items-center rounded-lg bg-slate-700/60"><Code2 size={14} className="text-slate-200" /></span><span><b className="block text-[10px] text-slate-200">open-source-toolkit</b><small className="text-[8px] text-slate-500">README · architecture</small></span></div>
                    <div className="mt-3 flex flex-wrap gap-1"><span className="rounded bg-blue-400/10 px-1.5 py-1 text-[8px] text-blue-200">TypeScript</span><span className="rounded bg-violet-400/10 px-1.5 py-1 text-[8px] text-violet-200">FastAPI</span><span className="rounded bg-emerald-400/10 px-1.5 py-1 text-[8px] text-emerald-200">RAG</span></div>
                    <div className="mt-3 space-y-1.5"><div className="h-1 w-full rounded bg-slate-700/60" /><div className="h-1 w-4/5 rounded bg-slate-700/50" /><div className="h-1 w-3/5 rounded bg-slate-700/40" /></div>
                  </div>
                  <div className="mt-3 flex items-center gap-1.5 text-[9px] text-emerald-200/80"><BadgeCheck size={12} /> Evidence linked to source files</div>
                </div>
                <div className="rounded-xl border border-white/[0.08] bg-[#111a2d] p-3.5">
                  <div className="flex items-center gap-2"><span className="grid h-7 w-7 place-items-center rounded-lg bg-violet-400/10 text-violet-200"><Sparkles size={14} /></span><span className="text-[10px] font-semibold text-slate-200">Story, not just stats</span></div>
                  <p className="mt-2.5 text-[9px] leading-4 text-slate-400">“The interesting part wasn’t adding a model. It was making every generated claim point back to a source.”</p>
                  <div className="mt-2 inline-flex items-center gap-1 text-[8px] text-indigo-200"><BookOpenText size={10} /> Draft insight · review before publishing</div>
                </div>
              </div>

              <div className="rounded-xl border border-white/[0.08] bg-[#111a2d] p-3.5">
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold text-slate-200"><Layers3 size={12} className="text-indigo-300" /> Community feed</span>
                  <span className="rounded bg-white/[0.05] px-1.5 py-1 text-[8px] text-slate-400">Concept</span>
                </div>
                <article className="mt-3 rounded-lg border border-white/[0.07] bg-[#0b1120] p-3">
                  <div className="flex items-center gap-2"><span className="grid h-7 w-7 place-items-center rounded-full bg-gradient-to-br from-cyan-400/30 to-indigo-400/30 text-[9px] font-bold text-cyan-100">JD</span><span className="flex-1"><b className="block text-[9px] text-slate-200">Jordan Developer</b><small className="text-[8px] text-slate-500">Building in public · 2h</small></span><span className="text-[8px] text-slate-500">Follow +</span></div>
                  <p className="mt-3 text-[10px] leading-[1.65] text-slate-300">A small lesson from shipping a retrieval pipeline: show the evidence, not just the generated answer.</p>
                  <div className="my-3 rounded-md border border-indigo-300/10 bg-indigo-400/[0.05] p-2 font-mono text-[8px] leading-4 text-indigo-100/75"><span className="text-violet-300">results</span> = retriever.search(query)<br /><span className="text-slate-500"># Inspect before you generate</span></div>
                  <div className="flex items-center gap-3 border-t border-white/[0.06] pt-2.5 text-[8px] text-slate-500"><span className="inline-flex items-center gap-1"><Heart size={10} /> Appreciate</span><span>Comment</span><span className="ml-auto">Project story</span></div>
                </article>
                <div className="mt-3 rounded-lg border border-cyan-200/20 bg-gradient-to-br from-cyan-300/[0.12] via-indigo-400/[0.09] to-blue-400/[0.04] p-3 shadow-[0_0_24px_rgba(34,211,238,.06)]">
                  <div className="flex items-center gap-2"><span className="grid h-6 w-6 place-items-center rounded-md border border-cyan-100/15 bg-cyan-200/10"><Blocks size={13} className="text-cyan-100" /></span><span className="text-[9px] font-semibold text-slate-100">Pay creators directly</span><span className="ml-auto rounded-full border border-amber-200/15 px-1.5 py-0.5 text-[7px] uppercase tracking-wider text-amber-100/80">MVP concept</span></div>
                  <p className="mt-2 text-[8px] leading-4 text-slate-300">Tip a developer or buy software, plugins, libraries, and services with a compatible wallet.</p>
                  <div className="mt-2.5 flex items-center gap-1.5 text-[7px] text-cyan-100/80"><span className="rounded border border-white/10 bg-[#0b1120]/60 px-1.5 py-1">Supporter</span><span className="h-px flex-1 border-t border-dashed border-cyan-200/40" /><span className="rounded border border-cyan-200/15 bg-cyan-200/[0.07] px-1.5 py-1">Public chain</span><span className="h-px flex-1 border-t border-dashed border-cyan-200/40" /><span className="rounded border border-white/10 bg-[#0b1120]/60 px-1.5 py-1">Creator</span></div>
                </div>
              </div>
            </div>
          </div>
          <div className="absolute -left-4 top-[28%] hidden items-center gap-2 rounded-lg border border-white/10 bg-[#111a2a] px-3 py-2 text-[9px] text-slate-300 shadow-xl sm:flex"><span className="h-1.5 w-1.5 rounded-full bg-emerald-300" /> source-linked insight</div>
          <div className="absolute -right-3 bottom-[15%] hidden items-center gap-2 rounded-lg border border-white/10 bg-[#111a2a] px-3 py-2 text-[9px] text-slate-300 shadow-xl sm:flex"><Heart size={11} className="text-pink-300" /> community appreciation</div>
        </div>
      </div>
    </section>
  )
}
