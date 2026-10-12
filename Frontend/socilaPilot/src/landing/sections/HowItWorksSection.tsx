import { ArrowRight, FileInput, MessageCircle, SearchCheck, Sparkles } from 'lucide-react'
import { SectionHeading } from '../components/SectionHeading'

const steps = [
  { number: '01', title: 'Bring your work', description: 'Share a public GitHub repository or provide project documentation.', icon: FileInput, detail: 'Repository · README · docs' },
  { number: '02', title: 'Understand it with AI', description: 'Retrieve relevant project context and surface technologies, decisions, and lessons.', icon: SearchCheck, detail: 'Evidence before generation' },
  { number: '03', title: 'Publish and connect', description: 'Review a technical post or case study, then share it with the developer community.', icon: Sparkles, detail: 'You stay in the editor seat' },
  { number: '04', title: 'Receive recognition', description: 'People discover the work, join the discussion, and can tip the creator directly.', icon: MessageCircle, detail: 'Engagement · optional tips' },
]

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="scroll-mt-24 border-b border-white/[0.06] bg-[#090e1a]">
      <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:px-10 lg:py-28">
        <SectionHeading eyebrow="HOW IT WORKS" title="From code to community support." centered>
          A simple path from the project you already built to the people who can learn from it.
        </SectionHeading>
        <div className="relative grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div className="pointer-events-none absolute left-[12%] right-[12%] top-7 hidden border-t border-dashed border-indigo-300/20 lg:block" />
          {steps.map(({ number, title, description, icon: Icon, detail }) => (
            <article key={number} className="relative rounded-2xl border border-white/[0.08] bg-[#0d1423] p-5 sm:p-6">
              <div className="relative z-10 flex items-center justify-between">
                <span className="grid h-14 w-14 place-items-center rounded-2xl border border-indigo-200/15 bg-[#101a2c] text-indigo-200 shadow-[0_0_28px_rgba(99,102,241,.08)]"><Icon size={21} /></span>
                <span className="font-mono text-xs tracking-wider text-slate-600">{number}</span>
              </div>
              <h3 className="mt-6 font-display text-base font-semibold text-white">{title}</h3>
              <p className="mt-2 min-h-[72px] text-xs leading-5 text-slate-400">{description}</p>
              <div className="mt-4 border-t border-white/[0.07] pt-3 text-[10px] text-indigo-200/70">{detail}</div>
              {number !== '04' && <ArrowRight className="absolute -right-[13px] top-7 z-20 hidden text-indigo-300/70 lg:block" size={16} />}
            </article>
          ))}
        </div>
        <div className="mt-6 flex justify-center">
          <a href="#rag" className="inline-flex items-center gap-2 text-xs font-medium text-indigo-200 transition-colors hover:text-white">See how the AI grounds the story <ArrowRight size={14} /></a>
        </div>
      </div>
    </section>
  )
}
