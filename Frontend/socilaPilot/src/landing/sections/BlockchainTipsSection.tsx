import { useState } from 'react'
import { ArrowDownLeft, ArrowRight, ArrowUpRight, Blocks, Check, Code2, Download, ExternalLink, KeyRound, Package, PlugZap, ShieldCheck, WalletCards, Wrench } from 'lucide-react'
import { SectionHeading } from '../components/SectionHeading'

const principles = [
  { icon: ArrowUpRight, title: 'Pay creators directly', copy: 'Tip a developer or pay for their software, libraries, plugins, or services.' },
  { icon: ShieldCheck, title: 'Transparent records', copy: 'Confirmed transactions can be inspected on the relevant public chain.' },
  { icon: KeyRound, title: 'Creator-controlled keys', copy: 'The platform does not need to collect or store a creator’s private key.' },
]

const products = [
  { id: 'library', name: 'React utility library', kind: 'Open-source library', price: '0.008 ETH', icon: Code2 },
  { id: 'plugin', name: 'Design-to-code plugin', kind: 'Developer plugin', price: '0.015 ETH', icon: PlugZap },
  { id: 'service', name: 'Code review session', kind: 'Developer service', price: '0.04 ETH', icon: Wrench },
  { id: 'software', name: 'Local dev toolkit', kind: 'Software download', price: '0.02 ETH', icon: Download },
]

export function BlockchainTipsSection() {
  const [paymentMode, setPaymentMode] = useState<'tip' | 'product'>('product')
  const [selectedProduct, setSelectedProduct] = useState(products[0])
  const [tipAmount, setTipAmount] = useState('0.005 ETH')

  return (
    <section id="creator-support" className="relative isolate scroll-mt-24 overflow-hidden border-y border-cyan-200/[0.12] bg-[#091321]">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_78%_35%,rgba(34,211,238,.14),transparent_34%),radial-gradient(ellipse_at_12%_78%,rgba(99,102,241,.12),transparent_35%)]" />
      <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:px-10 lg:py-28">
        <div className="mb-10 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-cyan-200/15 bg-cyan-200/[0.04] px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-lg border border-cyan-100/15 bg-cyan-200/10 text-cyan-100"><Blocks size={17} /></span>
            <div><strong className="block text-xs font-semibold text-white">Blockchain powers direct creator payments.</strong><span className="mt-1 block text-[10px] text-slate-400">Tip a developer or buy their software, plugins, libraries, and services.</span></div>
          </div>
          <span className="rounded-full border border-amber-100/15 bg-amber-100/[0.04] px-2.5 py-1 text-[8px] font-semibold uppercase tracking-wider text-amber-100/80">Proposed MVP capability</span>
        </div>
        <div className="grid items-center gap-12 lg:grid-cols-[.9fr_1.1fr] lg:gap-16">
          <div>
            <SectionHeading eyebrow="BLOCKCHAIN PAYMENTS FOR DEVELOPER WORK" title="Tip a developer—or buy what they build.">
              Support can go beyond appreciation. A community member can tip a creator or pay directly for a developer’s software, library, plugin, or service using a compatible wallet.
            </SectionHeading>
            <div className="space-y-5">
              {principles.map(({ icon: Icon, title, copy }) => (
                <div key={title} className="flex gap-3.5">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-cyan-200/10 bg-cyan-300/[0.06] text-cyan-200"><Icon size={16} /></span>
                  <div><h3 className="text-xs font-semibold text-slate-200">{title}</h3><p className="mt-1 text-xs leading-5 text-slate-500">{copy}</p></div>
                </div>
              ))}
            </div>
            <div className="mt-7 flex gap-2.5 rounded-lg border border-amber-200/15 bg-amber-200/[0.045] p-3.5">
              <ShieldCheck size={15} className="mt-0.5 shrink-0 text-amber-100/80" />
              <p className="text-[10px] leading-5 text-slate-400"><strong className="font-semibold text-amber-100">What blockchain does—and does not—verify:</strong> it can record a wallet transfer. It does not prove project authorship or that technical claims are true.</p>
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-[520px]">
            <div className="absolute -inset-10 rounded-full bg-cyan-400/[0.11] blur-3xl" />
            <div className="relative overflow-hidden rounded-2xl border border-cyan-100/15 bg-[#0b1422]/95 shadow-[0_25px_80px_-35px_rgba(0,0,0,.85)]">
              <div className="flex items-center justify-between border-b border-cyan-100/[0.08] bg-gradient-to-r from-cyan-300/[0.08] to-transparent px-5 py-4"><div className="flex items-center gap-2"><span className="grid h-7 w-7 place-items-center rounded-lg border border-cyan-100/15 bg-cyan-100/[0.08]"><Blocks size={15} className="text-cyan-100" /></span><strong className="text-xs text-white">Direct payments to developers</strong></div><span className="rounded-full border border-amber-200/15 bg-amber-300/[0.05] px-2 py-1 text-[8px] font-medium uppercase tracking-wider text-amber-100/80">Illustrative flow</span></div>
              <div className="p-5">
                <div className="mb-4 grid grid-cols-2 rounded-lg border border-white/[0.07] bg-[#07101d] p-1">
                  <button aria-pressed={paymentMode === 'tip'} onClick={() => setPaymentMode('tip')} className={`rounded-md px-3 py-2 text-[10px] font-medium transition-colors ${paymentMode === 'tip' ? 'bg-cyan-200/10 text-cyan-100' : 'text-slate-500 hover:text-slate-300'}`}>Tip a creator</button>
                  <button aria-pressed={paymentMode === 'product'} onClick={() => setPaymentMode('product')} className={`rounded-md px-3 py-2 text-[10px] font-medium transition-colors ${paymentMode === 'product' ? 'bg-cyan-200/10 text-cyan-100' : 'text-slate-500 hover:text-slate-300'}`}>Buy developer work</button>
                </div>
                <div className="mb-4 grid grid-cols-[1fr_auto_1fr_auto_1fr] items-center gap-2 rounded-lg border border-cyan-100/10 bg-[#07101d] px-3 py-3">
                  <div className="text-center"><span className="mx-auto grid h-8 w-8 place-items-center rounded-full border border-indigo-100/15 bg-indigo-200/[0.08] text-indigo-100"><WalletCards size={15} /></span><small className="mt-1.5 block text-[8px] text-slate-400">Supporter wallet</small></div>
                  <ArrowRight size={13} className="text-cyan-200/70" />
                  <div className="text-center"><span className="mx-auto grid h-8 w-8 place-items-center rounded-full border border-cyan-100/15 bg-cyan-200/[0.09] text-cyan-100"><Blocks size={15} /></span><small className="mt-1.5 block text-[8px] text-cyan-100/80">Blockchain network</small></div>
                  <ArrowRight size={13} className="text-cyan-200/70" />
                  <div className="text-center"><span className="mx-auto grid h-8 w-8 place-items-center rounded-full border border-violet-100/15 bg-violet-200/[0.08] text-violet-100"><ArrowDownLeft size={15} /></span><small className="mt-1.5 block text-[8px] text-slate-400">Creator wallet</small></div>
                </div>
                <div className="rounded-xl border border-white/[0.07] bg-[#10192a] p-4">
                  {paymentMode === 'product' ? (
                    <>
                      <div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-lg border border-violet-200/10 bg-violet-300/[0.08] text-violet-100"><Package size={17} /></span><div><strong className="block text-[10px] text-slate-100">Developer marketplace</strong><small className="mt-1 block text-[8px] text-slate-500">Illustrative products and services</small></div><span className="ml-auto rounded-full border border-cyan-100/10 px-2 py-1 text-[7px] text-cyan-100/80">PAY CREATOR</span></div>
                      <div className="mt-3 grid grid-cols-2 gap-2">
                        {products.map(({ id, name, kind, price, icon: ProductIcon }) => (
                          <button key={id} aria-pressed={selectedProduct.id === id} onClick={() => setSelectedProduct(products.find((product) => product.id === id) ?? products[0])} className={`rounded-lg border p-2.5 text-left transition-colors ${selectedProduct.id === id ? 'border-cyan-100/25 bg-cyan-200/[0.07]' : 'border-white/[0.06] bg-[#0b1120] hover:border-white/15'}`}>
                            <span className="flex items-center gap-1.5 text-[9px] font-medium text-slate-200"><ProductIcon size={11} className="text-cyan-200" />{kind}</span>
                            <span className="mt-1.5 block truncate text-[8px] text-slate-400">{name}</span>
                            <span className="mt-1 block text-[9px] font-semibold text-cyan-100">{price}</span>
                          </button>
                        ))}
                      </div>
                      <div className="mt-3 flex items-center justify-between rounded-lg border border-white/[0.06] bg-[#0b1120] px-3 py-2.5">
                        <div><span className="block text-[8px] text-slate-500">{selectedProduct.name}</span><strong className="mt-1 block text-[10px] text-slate-200">Payment to Jordan Developer</strong></div>
                        <span className="font-mono text-xs font-semibold text-cyan-100">{selectedProduct.price}</span>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-full border border-indigo-100/10 bg-gradient-to-br from-violet-300/30 to-cyan-300/20 text-xs font-semibold text-white">JD</span><div className="flex-1"><strong className="block text-xs text-slate-100">Jordan Developer</strong><small className="mt-1 block text-[9px] text-slate-500">Creator wallet connected</small></div><span className="inline-flex items-center gap-1 text-[8px] text-emerald-200"><Check size={11} /> Compatible wallet</span></div>
                      <div className="mt-4 rounded-lg border border-white/[0.06] bg-[#0b1120] p-3">
                        <div className="flex items-center justify-between"><span className="text-[9px] text-slate-500">Support this project story</span><span className="text-[8px] text-slate-600">Network · demo</span></div>
                        <p className="mt-2 text-[10px] leading-4 text-slate-300">“This saved me time debugging my own retrieval setup. Thanks for sharing the details.”</p>
                      </div>
                      <div className="mt-4">
                        <span className="text-[9px] font-medium text-slate-400">Choose a tip amount</span>
                        <div className="mt-2 grid grid-cols-3 gap-2">{['0.001 ETH', '0.005 ETH', '0.01 ETH'].map((amount) => <button key={amount} aria-pressed={tipAmount === amount} onClick={() => setTipAmount(amount)} className={`rounded-lg border py-2 text-[10px] ${tipAmount === amount ? 'border-indigo-300/30 bg-indigo-300/[0.09] text-indigo-100' : 'border-white/[0.1] bg-white/[0.025] text-slate-300'}`}>{amount}</button>)}</div>
                      </div>
                      <div className="mt-3 rounded-lg border border-white/[0.06] bg-[#0b1120] px-3 py-2.5"><div className="flex justify-between text-[9px]"><span className="text-slate-500">Tip amount</span><span className="font-mono text-cyan-100">{tipAmount}</span></div><div className="mt-2 flex justify-between text-[9px]"><span className="text-slate-500">To creator wallet</span><span className="font-mono text-slate-300">0x93…8f10</span></div></div>
                    </>
                  )}
                  <div className="mt-3 flex items-start gap-2 rounded-lg border border-cyan-200/10 bg-cyan-200/[0.035] p-2.5"><ArrowDownLeft size={12} className="mt-0.5 shrink-0 text-cyan-200" /><p className="text-[8px] leading-4 text-slate-400">Your wallet asks you to review and approve. SocialPilot never sees your private key.</p></div>
                  <button disabled className="mt-4 flex h-10 w-full cursor-not-allowed items-center justify-center gap-2 rounded-lg border border-cyan-100/10 bg-gradient-to-r from-cyan-400/10 to-indigo-400/10 text-[10px] font-semibold text-cyan-50/80"><WalletCards size={13} /> Wallet checkout · not live yet <ExternalLink size={11} /></button>
                </div>
                <div className="mt-3 flex items-center justify-between px-1 text-[8px] text-slate-500"><span>Buyer approval required · network fees may apply</span><span>Demo UI</span></div>
                <div className="mt-4 flex items-center gap-2 rounded-lg border border-emerald-200/10 bg-emerald-200/[0.035] px-3 py-2.5">
                  <span className="grid h-6 w-6 place-items-center rounded-full bg-emerald-200/10 text-emerald-200"><Check size={12} /></span>
                  <span className="flex-1"><strong className="block text-[9px] font-semibold text-emerald-100/90">After confirmation: transaction record</strong><small className="mt-0.5 block text-[8px] text-slate-500">A public record of the transfer—not proof of authorship</small></span>
                  <ArrowUpRight size={12} className="text-emerald-100/70" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
