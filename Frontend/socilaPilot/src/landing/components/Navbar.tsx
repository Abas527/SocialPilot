import { useState } from 'react'
import { ArrowUpRight, Menu, X } from 'lucide-react'

type NavbarProps = {
  onOpenWorkspace: () => void
}

const links = [
  { label: 'The idea', href: '#problem' },
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Technology', href: '#rag' },
  { label: 'Blockchain payments', href: '#creator-support' },
  { label: 'MVP', href: '#mvp' },
  { label: 'Vision', href: '#vision' },
]

export function Navbar({ onOpenWorkspace }: NavbarProps) {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.07] bg-[#080c18]/85 backdrop-blur-xl">
      <nav className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-5 sm:px-8 lg:px-10" aria-label="Main navigation">
        <a href="#top" className="group inline-flex items-center gap-2.5" aria-label="SocialPilot AI home">
          <span className="relative grid h-9 w-9 place-items-center rounded-xl border border-indigo-300/25 bg-gradient-to-br from-indigo-400/25 to-blue-500/10 shadow-lg shadow-indigo-950/30">
            <span className="font-display text-xs font-bold tracking-tight text-indigo-100">SP</span>
            <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border-2 border-[#080c18] bg-cyan-300" />
          </span>
          <span className="font-display text-[15px] font-semibold tracking-[-0.04em] text-white">social<span className="text-indigo-300">pilot</span><span className="ml-1 text-slate-400">AI</span></span>
        </a>

        <div className="hidden items-center gap-7 lg:flex">
          {links.map((link) => <a key={link.href} className="text-[13px] text-slate-400 transition-colors hover:text-white" href={link.href}>{link.label}</a>)}
        </div>

        <div className="hidden items-center gap-4 lg:flex">
          <button onClick={onOpenWorkspace} className="text-[13px] font-medium text-slate-300 transition-colors hover:text-white">Open workspace</button>
          <a href="#mvp" className="inline-flex h-10 items-center gap-2 rounded-lg border border-indigo-300/25 bg-indigo-400/10 px-4 text-[13px] font-semibold text-indigo-100 transition-all hover:border-indigo-200/50 hover:bg-indigo-400/15">
            Explore the MVP <ArrowUpRight size={15} />
          </a>
        </div>

        <button className="grid h-10 w-10 place-items-center rounded-lg border border-white/10 text-slate-200 lg:hidden" aria-label={menuOpen ? 'Close menu' : 'Open menu'} aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>
          {menuOpen ? <X size={19} /> : <Menu size={19} />}
        </button>
      </nav>
      {menuOpen && (
        <div className="border-t border-white/[0.07] bg-[#080c18] px-5 py-4 lg:hidden">
          <div className="mx-auto grid max-w-7xl gap-1">
            {links.map((link) => (
              <a key={link.href} href={link.href} onClick={() => setMenuOpen(false)} className="rounded-lg px-3 py-2.5 text-sm text-slate-300 hover:bg-white/[0.05]">{link.label}</a>
            ))}
            <button onClick={() => { setMenuOpen(false); onOpenWorkspace() }} className="mt-2 rounded-lg bg-indigo-400/10 px-3 py-3 text-left text-sm font-medium text-indigo-100">Open workspace</button>
          </div>
        </div>
      )}
    </header>
  )
}
