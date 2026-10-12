import { useState } from 'react'
import { Bookmark, Code2, Heart, MessageCircle, Plus, Search, Send, Sparkles, Users, UserRoundPlus } from 'lucide-react'
import { SectionHeading } from '../components/SectionHeading'

const feedTopics = ['All work', 'Project stories', 'Engineering lessons']

export function CommunitySection() {
  const [activeTopic, setActiveTopic] = useState(feedTopics[0])
  const [appreciated, setAppreciated] = useState(false)

  return (
    <section id="community" className="scroll-mt-24 border-b border-white/[0.06] bg-[#090e1a]">
      <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:px-10 lg:py-28">
        <div className="grid items-center gap-12 lg:grid-cols-[.85fr_1.15fr] lg:gap-16">
          <div>
            <SectionHeading eyebrow="A DEVELOPER COMMUNITY" title="More than a feed. A home for technical work.">
              Discover useful projects and the decisions behind them. Follow builders, exchange feedback, and make professional identity visible through what you create.
            </SectionHeading>
            <div className="space-y-4">
              {[
                ['Project-first profiles', 'Show what you built alongside what you know.'],
                ['Knowledge over noise', 'Surface practical lessons, code, and honest trade-offs.'],
                ['Discovery that opens doors', 'Find peers and work through shared technical interests.'],
              ].map(([title, copy]) => <div key={title} className="flex gap-3"><span className="mt-1 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-indigo-300/10 text-indigo-200"><Plus size={12} /></span><div><strong className="text-xs font-semibold text-slate-200">{title}</strong><p className="mt-1 text-xs leading-5 text-slate-500">{copy}</p></div></div>)}
            </div>
            <p className="mt-6 inline-flex items-center gap-1.5 text-[10px] text-slate-500"><Users size={13} className="text-indigo-300" /> Community screens shown here are illustrative—not live user activity.</p>
          </div>

          <div className="overflow-hidden rounded-2xl border border-white/[0.1] bg-[#0d1423] shadow-[0_28px_90px_-40px_rgba(0,0,0,.9)]">
            <div className="flex items-center justify-between border-b border-white/[0.07] px-4 py-3.5 sm:px-5">
              <div className="flex items-center gap-2.5"><span className="grid h-8 w-8 place-items-center rounded-lg border border-indigo-300/10 bg-indigo-300/[0.08] text-indigo-200"><Code2 size={15} /></span><span className="font-display text-xs font-semibold text-white">The workshop</span></div>
              <div className="flex items-center gap-3 text-slate-500"><Search size={14} /><span className="text-[9px]">Explore</span><span className="grid h-7 w-7 place-items-center rounded-full bg-gradient-to-br from-violet-300/40 to-cyan-300/30 text-[8px] font-bold text-white">JD</span></div>
            </div>
            <div className="flex gap-2 overflow-x-auto border-b border-white/[0.06] px-4 py-3 sm:px-5">
              {feedTopics.map((topic) => <button key={topic} onClick={() => setActiveTopic(topic)} className={`shrink-0 rounded-full border px-3 py-1.5 text-[9px] transition-colors ${activeTopic === topic ? 'border-indigo-300/25 bg-indigo-300/10 text-indigo-100' : 'border-white/[0.06] text-slate-500 hover:text-slate-300'}`}>{topic}</button>)}
              <span className="ml-auto hidden items-center text-[8px] text-slate-600 sm:flex">SAMPLE FEED</span>
            </div>

            <div className="space-y-3 p-3 sm:p-4">
              <article className="rounded-xl border border-white/[0.07] bg-[#10192a] p-4 sm:p-5">
                <div className="flex items-start gap-2.5">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-cyan-200/10 bg-gradient-to-br from-cyan-300/25 to-indigo-300/25 text-[10px] font-bold text-cyan-100">JD</span>
                  <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-1.5"><strong className="text-[10px] text-slate-100">Jordan Developer</strong><span className="text-[8px] text-slate-600">·</span><span className="text-[8px] text-slate-500">Open-source builder</span><button className="ml-auto inline-flex items-center gap-1 rounded-md border border-indigo-300/15 px-2 py-1 text-[8px] text-indigo-200"><UserRoundPlus size={10} /> Follow</button></div><span className="mt-1 block text-[8px] text-slate-600">Project story · illustrative content</span></div>
                </div>
                <p className="mt-4 text-xs leading-[1.8] text-slate-300 sm:text-[13px]">A lesson from building a retrieval pipeline: generated answers are easier to trust when you can inspect the evidence that shaped them.</p>
                <div className="my-4 rounded-lg border border-indigo-200/[0.08] bg-[#090f1e] p-3">
                  <div className="mb-2 flex items-center gap-2 text-[8px] text-indigo-200"><Code2 size={11} /> PROJECT NOTE · evidence-first generation</div>
                  <pre className="overflow-x-auto font-mono text-[9px] leading-5 text-slate-400"><span className="text-violet-300">matches</span> = retriever.search(query)<br /><span className="text-slate-500"># inspect the sources before generating</span><br /><span className="text-cyan-200">draft</span> = model.complete(context=matches)</pre>
                  <div className="mt-2 flex items-center gap-1.5 text-[8px] text-slate-600"><Bookmark size={10} /> Built from a project · source references available</div>
                </div>
                <div className="flex items-center justify-between border-t border-white/[0.06] pt-3">
                  <div className="flex gap-4"><button onClick={() => setAppreciated(!appreciated)} aria-pressed={appreciated} className={`inline-flex items-center gap-1.5 text-[9px] transition-colors ${appreciated ? 'text-pink-300' : 'text-slate-500 hover:text-pink-300'}`}><Heart size={13} fill={appreciated ? 'currentColor' : 'none'} />{appreciated ? 'Appreciated' : 'Appreciate'}</button><button className="inline-flex items-center gap-1.5 text-[9px] text-slate-500 hover:text-slate-300"><MessageCircle size={13} />Discuss</button></div>
                  <button className="inline-flex items-center gap-1.5 text-[9px] text-indigo-200"><Send size={12} /> Share</button>
                </div>
              </article>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-white/[0.07] bg-[#10192a] p-3.5">
                  <span className="text-[8px] uppercase tracking-wider text-slate-500">FEATURED PROJECT</span>
                  <div className="mt-2 flex items-center gap-2"><span className="grid h-8 w-8 place-items-center rounded-lg bg-violet-300/10 text-violet-200"><Code2 size={15} /></span><div><b className="block text-[9px] text-slate-200">Tiny Vector Search</b><small className="text-[8px] text-slate-500">A build log, not just a repo</small></div></div>
                </div>
                <div className="rounded-xl border border-indigo-300/10 bg-gradient-to-br from-indigo-300/[0.08] to-transparent p-3.5">
                  <div className="flex items-center gap-1.5 text-[9px] text-indigo-100"><Sparkles size={12} /> Turn project into a post</div>
                  <p className="mt-1.5 text-[8px] leading-4 text-slate-500">AI-assisted writing begins with your source material.</p>
                  <a href="#mvp" className="mt-2 inline-block text-[8px] text-indigo-200">See planned MVP ↗</a>
                </div>
              </div>
            </div>
            <div className="border-t border-white/[0.06] px-4 py-2.5 text-center text-[8px] text-slate-600">Illustrative product interface · features shown are part of the proposed MVP</div>
          </div>
        </div>
      </div>
    </section>
  )
}
