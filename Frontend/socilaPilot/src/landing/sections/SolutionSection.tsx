import { ArrowDownRight, ArrowUpRight, Blocks, BookOpenText, Network, Sparkles } from 'lucide-react'
import { SectionHeading } from '../components/SectionHeading'

const pillars = [
  {
    number: '01',
    title: 'Turn projects into stories',
    body: 'Use project documentation and code evidence to shape technical posts, engineering case studies, and clear project descriptions.',
    icon: Sparkles,
    className: 'from-violet-400/15 via-indigo-400/[0.04] to-transparent',
    iconClass: 'border-violet-200/15 bg-violet-300/10 text-violet-200',
    tag: 'AI + project evidence',
  },
  {
    number: '02',
    title: 'Build in public, grow together',
    body: 'Share project showcases and lessons in a developer-focused community built for useful technical exchange and discovery.',
    icon: Network,
    className: 'from-blue-400/15 via-cyan-400/[0.04] to-transparent',
    iconClass: 'border-cyan-200/15 bg-cyan-300/10 text-cyan-200',
    tag: 'Profiles + community',
  },
  {
    number: '03',
    title: 'Blockchain payments for developer work',
    body: 'Tip a creator or pay wallet-to-wallet for software, libraries, plugins, and services. The public chain provides an inspectable transaction record.',
    icon: Blocks,
    className: 'from-cyan-300/[0.18] via-blue-400/[0.07] to-transparent',
    iconClass: 'border-cyan-200/25 bg-cyan-300/[0.13] text-cyan-100',
    tag: 'Tips + creator purchases',
  },
]

export function SolutionSection() {
  return (
    <section id="solution" className="scroll-mt-24 border-b border-white/[0.06]">
      <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:px-10 lg:py-28">
        <SectionHeading eyebrow="THE SOLUTION" title="One platform. Three connected experiences.">
          Create a loop: make the work understandable, share it with people who care, and let appreciation become support.
        </SectionHeading>
        <div className="grid gap-4 lg:grid-cols-3">
          {pillars.map(({ number, title, body, icon: Icon, className, iconClass, tag }, index) => (
            <article key={number} className={`relative overflow-hidden rounded-2xl border border-white/[0.09] bg-gradient-to-br ${className} p-6 sm:p-7`}>
              <div className="absolute right-5 top-4 font-display text-6xl font-semibold tracking-[-.08em] text-white/[0.035]">{number}</div>
              <div className={`grid h-12 w-12 place-items-center rounded-xl border ${iconClass}`}><Icon size={21} /></div>
              <span className="mt-6 inline-flex rounded-full border border-white/[0.08] bg-black/10 px-2.5 py-1 text-[9px] font-medium uppercase tracking-wider text-slate-400">{tag}</span>
              <h3 className="mt-4 max-w-[250px] font-display text-xl font-semibold leading-snug tracking-tight text-white">{title}</h3>
              <p className="mt-3 min-h-[84px] text-sm leading-6 text-slate-400">{body}</p>
              <div className="mt-6 flex items-center gap-3 text-indigo-200/70">
                <div className="h-px flex-1 bg-white/[0.08]" />
                {index < 2 ? <ArrowDownRight size={15} /> : <ArrowUpRight size={15} />}
              </div>
            </article>
          ))}
        </div>
        <div className="mt-5 flex flex-col gap-3 rounded-xl border border-indigo-300/10 bg-indigo-400/[0.045] px-5 py-4 sm:flex-row sm:items-center">
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-indigo-300/10 text-indigo-200"><BookOpenText size={15} /></span>
          <p className="text-xs leading-5 text-slate-400"><strong className="font-semibold text-slate-200">One connected journey.</strong> Stories give the community something meaningful to discover; community recognition gives creators a reason to keep sharing.</p>
        </div>
      </div>
    </section>
  )
}
