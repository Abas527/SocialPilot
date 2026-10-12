import type { ReactNode } from 'react'

type SectionHeadingProps = {
  eyebrow: string
  title: string
  children?: ReactNode
  centered?: boolean
}

export function SectionHeading({ eyebrow, title, children, centered = false }: SectionHeadingProps) {
  return (
    <div className={`mb-12 max-w-2xl ${centered ? 'mx-auto text-center' : ''}`}>
      <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-indigo-400/20 bg-indigo-400/[0.07] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-indigo-200">
        <span className="h-1.5 w-1.5 rounded-full bg-indigo-300" />
        {eyebrow}
      </div>
      <h2 className="text-balance font-display text-3xl font-semibold leading-tight tracking-[-0.04em] text-white sm:text-4xl lg:text-[44px]">
        {title}
      </h2>
      {children && <div className={`mt-4 text-base leading-7 text-slate-400 ${centered ? 'mx-auto max-w-xl' : ''}`}>{children}</div>}
    </div>
  )
}
