import { ArrowUpRight, BadgeCheck, BookMarked, BriefcaseBusiness, Fingerprint, FolderGit2, HandCoins } from 'lucide-react'
import { SectionHeading } from '../components/SectionHeading'

const futureIdeas = [
  { icon: FolderGit2, title: 'Evidence-rich project history', copy: 'Keep source context and meaningful project changes connected over time.' },
  { icon: BadgeCheck, title: 'Contribution attestations', copy: 'Explore ways to make real contributions easier to verify.' },
  { icon: HandCoins, title: 'Paid knowledge and mentorship', copy: 'Let developers offer useful resources and time on their terms.' },
  { icon: BriefcaseBusiness, title: 'Discovery through real work', copy: 'Help opportunities find people through the projects they can show.' },
]

export function VisionSection() {
  return (
    <section id="vision" className="scroll-mt-24 border-b border-white/[0.06]">
      <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:px-10 lg:py-28">
        <div className="grid gap-12 lg:grid-cols-[.95fr_1.05fr] lg:items-center">
          <div>
            <SectionHeading eyebrow="THE LONG-TERM VISION" title="From sharing work to a professional identity built on what you do.">
              A developer’s professional story could grow from a living record of projects, engineering decisions, and knowledge shared—not just a resume or self-reported list of skills.
            </SectionHeading>
            <div className="flex items-start gap-3 rounded-xl border border-indigo-300/10 bg-indigo-300/[0.04] p-4">
              <Fingerprint size={17} className="mt-0.5 shrink-0 text-indigo-200" />
              <p className="text-xs leading-5 text-slate-400"><strong className="text-slate-200">A possibility, not a promise.</strong> Portable credentials or independent attestations would need careful design, consent, and credible verification.</p>
            </div>
          </div>
          <div>
            <div className="mb-3 flex items-center justify-between px-1"><span className="text-[10px] font-semibold uppercase tracking-[.15em] text-slate-400">Possible future directions</span><span className="text-[9px] text-slate-600">Beyond the initial MVP</span></div>
            <div className="space-y-2.5">
              {futureIdeas.map(({ icon: Icon, title, copy }, index) => (
                <article key={title} className="group flex gap-3.5 rounded-xl border border-white/[0.07] bg-[#0c1220] p-4 transition-colors hover:border-indigo-200/15 hover:bg-[#0e1627] sm:p-4.5">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-white/[0.07] bg-white/[0.025] text-indigo-200/80 group-hover:border-indigo-200/15 group-hover:bg-indigo-300/[0.07]"><Icon size={17} /></span>
                  <div className="flex-1"><div className="flex items-center gap-2"><span className="font-mono text-[8px] text-slate-600">0{index + 1}</span><h3 className="text-xs font-semibold text-slate-200">{title}</h3></div><p className="mt-1.5 text-[10px] leading-4 text-slate-500">{copy}</p></div>
                  <ArrowUpRight className="mt-1 shrink-0 text-slate-700 transition-colors group-hover:text-indigo-200/70" size={14} />
                </article>
              ))}
            </div>
            <div className="mt-3 flex items-center gap-2 text-[9px] text-slate-600"><BookMarked size={12} /> Built on evidence and consent, not hype.</div>
          </div>
        </div>
      </div>
    </section>
  )
}
