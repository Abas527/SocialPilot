import { ArrowRight, BookOpen, Check, CircleUserRound, Code2, Database, HeartHandshake, MessageSquare, Network, Sparkles, WalletCards } from 'lucide-react'
import { SectionHeading } from '../components/SectionHeading'

const featureGroups = [
  {
    icon: Sparkles,
    title: 'AI Project Studio',
    summary: 'Make technical work easier to explain.',
    items: ['Public repo or docs input', 'RAG-based evidence retrieval', 'Project analysis and story drafts', 'Edit before you publish'],
    color: 'violet',
  },
  {
    icon: Network,
    title: 'Developer Community',
    summary: 'Give useful work a place to travel.',
    items: ['Developer profiles', 'Project showcases and feed', 'Likes and comments', 'Following and discovery'],
    color: 'blue',
  },
  {
    icon: WalletCards,
    title: 'Blockchain Payments',
    summary: 'Tip creators and buy developer-made products.',
    items: ['Compatible wallet connection', 'Tips and direct product payments', 'Services, software, libraries, plugins', 'Transaction verification and history'],
    color: 'cyan',
  },
]

const stack = [
  { icon: Code2, label: 'Modular API', value: 'FastAPI' },
  { icon: Database, label: 'App data', value: 'SQLite' },
  { icon: BookOpen, label: 'Project context', value: 'Local RAG retrieval' },
  { icon: Sparkles, label: 'Development model', value: 'Ollama · local LLM' },
]

export function MVPSection() {
  return (
    <section id="mvp" className="scroll-mt-24 border-b border-white/[0.06] bg-[#090e1a]">
      <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:px-10 lg:py-28">
        <div className="grid gap-10 lg:grid-cols-[.72fr_1.28fr] lg:gap-14">
          <div>
            <SectionHeading eyebrow="THE MVP" title="Start focused. Build something useful.">
              The first release connects project understanding with sharing and community feedback—without trying to build every creator tool at once.
            </SectionHeading>
            <div className="rounded-xl border border-white/[0.08] bg-[#0d1423] p-5">
              <div className="flex items-center gap-2"><span className="grid h-8 w-8 place-items-center rounded-lg bg-indigo-300/10 text-indigo-200"><Code2 size={15} /></span><div><span className="text-[9px] font-semibold uppercase tracking-wider text-indigo-200">Development architecture</span><strong className="mt-1 block text-xs text-white">Practical, modular building blocks</strong></div></div>
              <div className="mt-4 grid grid-cols-2 gap-2">
                {stack.map(({ icon: Icon, label, value }) => <div key={label} className="rounded-lg border border-white/[0.06] bg-white/[0.015] p-3"><Icon size={13} className="text-slate-400" /><small className="mt-2 block text-[8px] text-slate-500">{label}</small><strong className="mt-1 block text-[9px] font-medium text-slate-300">{value}</strong></div>)}
              </div>
              <p className="mt-3 text-[9px] leading-4 text-slate-500">Local development keeps model experimentation practical. The RAG layer retrieves and checks project context before generation.</p>
            </div>
          </div>
          <div>
            <div className="mb-4 flex items-center justify-between"><span className="text-[10px] font-semibold uppercase tracking-[.15em] text-slate-400">Proposed initial feature scope</span><span className="rounded-full border border-amber-200/15 bg-amber-300/[0.05] px-2.5 py-1 text-[8px] font-medium text-amber-100/80">Planned / in development</span></div>
            <div className="grid gap-3 md:grid-cols-3">
              {featureGroups.map(({ icon: Icon, title, summary, items, color }) => (
                <article key={title} className="rounded-xl border border-white/[0.08] bg-[#0d1423] p-4 sm:p-5">
                  <span className={`grid h-10 w-10 place-items-center rounded-xl border ${color === 'violet' ? 'border-violet-200/10 bg-violet-300/[0.08] text-violet-200' : color === 'blue' ? 'border-blue-200/10 bg-blue-300/[0.08] text-blue-200' : 'border-cyan-200/10 bg-cyan-300/[0.08] text-cyan-200'}`}><Icon size={17} /></span>
                  <h3 className="mt-4 font-display text-sm font-semibold text-white">{title}</h3>
                  <p className="mt-1.5 min-h-[36px] text-[10px] leading-4 text-slate-500">{summary}</p>
                  <ul className="mt-4 space-y-2.5 border-t border-white/[0.06] pt-4">
                    {items.map((item) => <li key={item} className="flex gap-2 text-[9px] leading-4 text-slate-400"><Check size={12} className="mt-0.5 shrink-0 text-emerald-300/80" />{item}</li>)}
                  </ul>
                </article>
              ))}
            </div>
            <div className="mt-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="flex -space-x-1.5 text-slate-500"><CircleUserRound size={17} /><MessageSquare size={17} /><HeartHandshake size={17} /></div>
                <p className="flex-1 text-[10px] leading-5 text-slate-400"><strong className="text-slate-300">Scope note:</strong> Community networking, wallet tips, and developer-product payments are proposed MVP scope; this concept preview is not a live marketplace.</p>
                <a href="#vision" className="inline-flex shrink-0 items-center gap-1.5 text-[10px] text-indigo-200 hover:text-white">See what could come next <ArrowRight size={13} /></a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
