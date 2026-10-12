import type { ReactNode } from 'react'
import { AlertTriangle, ArrowRight, Braces, Check, FileCode2, FileText, GitBranch, Lightbulb, Search, Sparkles } from 'lucide-react'
import { SectionHeading } from '../components/SectionHeading'

const pipeline = [
  { label: 'Repository', icon: GitBranch },
  { label: 'Documents', icon: FileText },
  { label: 'RAG retrieval', icon: Search },
  { label: 'AI analysis', icon: Sparkles },
  { label: 'Useful story', icon: Braces },
]

export function RagSection() {
  return (
    <section id="rag" className="scroll-mt-24 border-b border-white/[0.06]">
      <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:px-10 lg:py-28">
        <SectionHeading eyebrow="TECHNICAL INNOVATION" title="AI that starts with your work, not just a prompt.">
          Retrieval-augmented generation (RAG) finds relevant project material first, then gives that evidence to the language model as context.
        </SectionHeading>

        <div className="mb-7 grid gap-2 sm:grid-cols-5">
          {pipeline.map(({ label, icon: Icon }, index) => (
            <div key={label} className="relative flex items-center gap-3 rounded-xl border border-white/[0.08] bg-[#0d1423] px-3 py-3 sm:flex-col sm:items-start sm:gap-4 sm:px-4 sm:py-4">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-indigo-300/10 bg-indigo-300/[0.07] text-indigo-200"><Icon size={16} /></span>
              <span className="text-xs font-medium text-slate-200">{label}</span>
              {index < pipeline.length - 1 && <ArrowRight className="absolute -right-[11px] z-10 hidden text-slate-600 sm:block" size={14} />}
              {index < pipeline.length - 1 && <ArrowRight className="ml-auto text-slate-600 sm:hidden" size={14} />}
            </div>
          ))}
        </div>

        <div className="grid gap-5 lg:grid-cols-[.8fr_1.2fr]">
          <div className="rounded-2xl border border-white/[0.08] bg-[#0d1423] p-6 sm:p-7">
            <div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl border border-violet-300/15 bg-violet-300/[0.08] text-violet-200"><Lightbulb size={18} /></span><div><span className="text-[10px] font-semibold uppercase tracking-[.14em] text-violet-200">Why RAG?</span><h3 className="mt-1 font-display text-base font-semibold text-white">Context before copy.</h3></div></div>
            <p className="mt-5 text-sm leading-6 text-slate-400">Rather than relying only on a short prompt, the system can retrieve relevant text from a README, supported source files, documentation, and tests before asking a model to draft.</p>
            <ul className="mt-5 space-y-3">
              {[
                'Find the project details related to the question.',
                'Include source excerpts so claims can be reviewed.',
                'Flag unknowns rather than filling gaps with guesses.',
              ].map((line) => <li key={line} className="flex gap-2.5 text-xs leading-5 text-slate-300"><Check size={14} className="mt-0.5 shrink-0 text-emerald-300" />{line}</li>)}
            </ul>
            <div className="mt-6 rounded-lg border border-amber-200/10 bg-amber-300/[0.05] p-3.5">
              <div className="flex gap-2 text-amber-100"><AlertTriangle size={14} className="mt-0.5 shrink-0" /><strong className="text-[11px]">Grounding helps. It is not a guarantee.</strong></div>
              <p className="mt-2 pl-[22px] text-[10px] leading-5 text-slate-400">Generated content can still be wrong or incomplete. Developers review every draft; unsupported claims should be challenged, not published as facts.</p>
            </div>
          </div>

          <div className="overflow-hidden rounded-2xl border border-white/[0.08] bg-[#0d1423]">
            <div className="flex items-center justify-between border-b border-white/[0.07] px-5 py-4">
              <div className="flex items-center gap-2.5"><span className="grid h-8 w-8 place-items-center rounded-lg bg-cyan-300/[0.08] text-cyan-200"><FileCode2 size={15} /></span><div><strong className="block text-xs text-white">Project analysis</strong><small className="text-[9px] text-slate-500">Illustrative sample · source evidence</small></div></div>
              <span className="rounded-full border border-emerald-200/15 bg-emerald-300/[0.06] px-2 py-1 text-[8px] font-medium text-emerald-200">Needs human review</span>
            </div>
            <div className="grid gap-4 p-5 sm:grid-cols-2">
              <AnalysisItem title="Project purpose" body="A toolkit that turns project documentation into source-linked technical content." icon={<Braces size={13} />} />
              <AnalysisItem title="Technologies detected" body="React · FastAPI · SQLite · local LLM" icon={<FileCode2 size={13} />} />
              <AnalysisItem title="Architecture insight" body="Retrieval and evidence checks precede content generation." icon={<GitBranch size={13} />} />
              <AnalysisItem title="Engineering decision" body="Keep generated claims reviewable with their retrieved context." icon={<Lightbulb size={13} />} />
            </div>
            <div className="mx-5 rounded-lg border border-white/[0.07] bg-[#0a1020] p-3.5">
              <div className="mb-2 flex items-center justify-between"><span className="text-[9px] font-semibold uppercase tracking-wider text-slate-400">Supporting source references</span><span className="text-[8px] text-emerald-200/80">2 excerpts</span></div>
              <div className="space-y-2 font-mono text-[9px] leading-4">
                <div className="flex gap-2 rounded bg-white/[0.025] px-2.5 py-2"><span className="shrink-0 text-indigo-300">README.md:12</span><span className="text-slate-400">“Pipeline: ingest → chunk/index → analyze → generate → verify claims...”</span></div>
                <div className="flex gap-2 rounded bg-white/[0.025] px-2.5 py-2"><span className="shrink-0 text-indigo-300">core/evidence.py</span><span className="text-slate-400">Claim-to-source excerpt checks and invented-number detection.</span></div>
              </div>
            </div>
            <div className="m-5 flex flex-col gap-2 rounded-lg border border-amber-200/10 bg-amber-200/[0.035] px-3 py-2.5 sm:flex-row sm:items-center">
              <span className="text-[9px] font-semibold uppercase tracking-wider text-amber-100/80">Unknowns</span>
              <span className="text-[9px] leading-4 text-slate-400">No independently measured user impact is provided in the sample sources.</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function AnalysisItem({ title, body, icon }: { title: string; body: string; icon: ReactNode }) {
  return <div className="rounded-lg border border-white/[0.06] bg-white/[0.015] p-3"><div className="flex items-center gap-1.5 text-indigo-200">{icon}<span className="text-[9px] font-semibold uppercase tracking-wider text-slate-400">{title}</span></div><p className="mt-2 text-[10px] leading-4 text-slate-300">{body}</p></div>
}
