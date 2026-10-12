import { Files, MessageSquareText, Radar } from 'lucide-react'
import { SectionHeading } from '../components/SectionHeading'

const problems = [
  { icon: Files, number: '01', title: 'Work is scattered.', body: 'Projects live in repositories, docs, portfolios, and disconnected social platforms. The context is spread across too many places.', color: 'text-blue-200 bg-blue-300/10 border-blue-300/15' },
  { icon: MessageSquareText, number: '02', title: 'Technical work is hard to communicate.', body: 'A commit shows what changed. It rarely explains the trade-offs, lessons, or decisions that made the work meaningful.', color: 'text-violet-200 bg-violet-300/10 border-violet-300/15' },
  { icon: Radar, number: '03', title: 'Good work can go unnoticed.', body: 'Useful contributions do not always reach the right people—and there is rarely a direct way for an audience to support the creator.', color: 'text-cyan-200 bg-cyan-300/10 border-cyan-300/15' },
]

export function ProblemSection() {
  return (
    <section id="problem" className="scroll-mt-24 border-b border-white/[0.06] bg-[#090e1a]">
      <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:px-10 lg:py-28">
        <SectionHeading eyebrow="THE PROBLEM" title="Developers build amazing things. Their stories often get lost.">
          The value of a project is more than its source code. The thinking behind it deserves a place in the conversation.
        </SectionHeading>
        <div className="grid gap-4 md:grid-cols-3">
          {problems.map(({ icon: Icon, number, title, body, color }) => (
            <article key={number} className="group rounded-2xl border border-white/[0.08] bg-[#0d1423] p-6 transition-all duration-300 hover:-translate-y-1 hover:border-white/[0.15] hover:bg-[#10192b] sm:p-7">
              <div className="flex items-center justify-between">
                <span className={`grid h-11 w-11 place-items-center rounded-xl border ${color}`}><Icon size={19} /></span>
                <span className="font-mono text-[10px] tracking-widest text-slate-600">{number}</span>
              </div>
              <h3 className="mt-7 font-display text-lg font-semibold tracking-tight text-white">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-slate-400">{body}</p>
              <div className="mt-7 h-px w-12 bg-gradient-to-r from-indigo-300/50 to-transparent transition-all group-hover:w-20" />
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
