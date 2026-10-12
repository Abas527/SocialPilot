import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, ExternalLink, HeartHandshake, Loader2, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useMyProfile, patchPostCaches } from '../../hooks/usePosts'
import { chainConfig } from '../../services/community'
import { api } from '../../services/api'
import { errorMessage, formatEth } from '../../lib/format'
import type { Post, PreparedTip, WalletProvider } from '../../types'

const PRESETS = ['0.001', '0.005', '0.01']
type Step = 'form' | 'wallet' | 'confirming' | 'done'

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
// The API answers 409 while the transaction is unseen or unconfirmed; keep asking.
const PENDING = /not yet available|not confirmed yet|has not succeeded/i

async function ensureSepolia(provider: WalletProvider, chainId: number) {
  const hex = `0x${chainId.toString(16)}`
  const current = await provider.request({ method: 'eth_chainId' })
  if (current === hex) return
  try {
    await provider.request({ method: 'wallet_switchEthereumChain', params: [{ chainId: hex }] })
  } catch {
    throw new Error('Switch your wallet to the Sepolia test network and try again.')
  }
}

export function TipModal({ post, onClose }: { post: Post; onClose: () => void }) {
  const qc = useQueryClient()
  const me = useMyProfile()
  const chain = useQuery({ queryKey: ['chain-config'], queryFn: chainConfig, staleTime: 300_000 })
  const [amount, setAmount] = useState('0.005')
  const [message, setMessage] = useState('')
  const [step, setStep] = useState<Step>('form')
  const [error, setError] = useState('')
  const [txHash, setTxHash] = useState('')
  const cancelled = useRef(false)
  const dialog = useRef<HTMLDivElement>(null)

  useEffect(() => {
    cancelled.current = false
    dialog.current?.focus()
    return () => { cancelled.current = true }
  }, [])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape' && step !== 'wallet' && step !== 'confirming') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, step])

  const walletLinked = Boolean(me.data?.wallet_address)
  const maxMessage = chain.data?.max_tip_message_chars ?? 140
  const valid = /^\d+(\.\d{1,18})?$/.test(amount) && Number(amount) > 0

  const send = async () => {
    setError('')
    const provider = window.ethereum
    if (!provider) { setError('Install an EVM wallet such as MetaMask to send a tip.'); return }
    try {
      setStep('wallet')
      const prepared = await api<PreparedTip>('/tips/prepare', {
        method: 'POST',
        body: JSON.stringify({ post_id: post.post_id, amount_eth: amount, message: message.trim() || null }),
      })
      await ensureSepolia(provider, prepared.chain_id)
      const accounts = await provider.request({ method: 'eth_requestAccounts' })
      const from = Array.isArray(accounts) ? String(accounts[0] ?? '') : ''
      if (from.toLowerCase() !== prepared.from.toLowerCase()) {
        throw new Error('Select the wallet you verified in SocialPilot, then try again.')
      }
      const hash = await provider.request({
        method: 'eth_sendTransaction',
        params: [{ from: prepared.from, to: prepared.to, value: prepared.value }],
      })
      if (typeof hash !== 'string') throw new Error('The wallet did not return a transaction hash.')
      setTxHash(hash)
      setStep('confirming')
      for (let attempt = 0; attempt < 60 && !cancelled.current; attempt += 1) {
        try {
          await api(`/tips/${prepared.intent_id}/verify`, { method: 'POST', body: JSON.stringify({ tx_hash: hash }) })
          patchPostCaches(qc, post.post_id, (p) => ({
            ...p, tip_count: p.tip_count + 1, tip_total_wei: (BigInt(p.tip_total_wei) + BigInt(prepared.amount_wei)).toString(),
          }))
          void qc.invalidateQueries({ queryKey: ['post-tips', post.post_id] })
          setStep('done')
          return
        } catch (cause) {
          if (!PENDING.test(errorMessage(cause))) throw cause
          await sleep(4000)
        }
      }
      if (!cancelled.current) throw new Error('Still waiting for confirmations. Your transaction was sent; check the Wallet page later.')
    } catch (cause) {
      const text = errorMessage(cause)
      setError(/user rejected|denied/i.test(text) ? 'The request was cancelled in your wallet.' : text)
      setStep('form')
    }
  }

  const busy = step === 'wallet' || step === 'confirming'
  return (
    <div className="dc-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose() }}>
      <div ref={dialog} tabIndex={-1} className="dc-modal" role="dialog" aria-modal="true" aria-labelledby="tip-title">
        {!busy && <button className="dc-modal-close" onClick={onClose} aria-label="Close"><X size={18} /></button>}
        <h2 id="tip-title"><HeartHandshake size={20} aria-hidden="true" /> Tip @{post.author.username}</h2>

        {step === 'done' ? (
          <div className="dc-tip-done">
            <CheckCircle2 size={34} aria-hidden="true" />
            <p><strong>{amount} ETH sent.</strong> Verified on {chain.data?.network ?? 'Sepolia'}.</p>
            <a href={`https://sepolia.etherscan.io/tx/${txHash}`} target="_blank" rel="noopener noreferrer">View transaction <ExternalLink size={12} /></a>
            <button className="dc-btn dc-btn-primary" onClick={onClose}>Done</button>
          </div>
        ) : step === 'confirming' ? (
          <div className="dc-tip-done" role="status">
            <Loader2 size={30} className="dc-spin" aria-hidden="true" />
            <p><strong>Waiting for {chain.data?.min_confirmations ?? 2} confirmations…</strong></p>
            <small>This usually takes under a minute. You can keep this window open.</small>
          </div>
        ) : !walletLinked && !me.isLoading ? (
          <div className="dc-tip-done">
            <p>Link and verify your wallet first so tips are tied to your account.</p>
            <Link className="dc-btn dc-btn-primary" to="/app/wallet" onClick={onClose}>Open Wallet</Link>
          </div>
        ) : (
          <>
            <p className="dc-muted">Sends test ETH on {chain.data?.network ?? 'Sepolia'} directly to the author's verified wallet. No real money.</p>
            <div className="dc-presets" role="group" aria-label="Amount presets">
              {PRESETS.map((preset) => (
                <button key={preset} type="button" className={amount === preset ? 'on' : ''} onClick={() => setAmount(preset)}>{preset} ETH</button>
              ))}
            </div>
            <label className="dc-field">Amount (ETH)
              <input inputMode="decimal" value={amount} onChange={(event) => setAmount(event.target.value.trim())} aria-invalid={!valid} />
            </label>
            {chain.data && valid && BigInt(Math.round(Number(amount) * 1e9)) * 10n ** 9n > BigInt(chain.data.max_tip_wei) && (
              <p className="dc-error">The testnet limit is {formatEth(chain.data.max_tip_wei)} ETH per tip.</p>
            )}
            <label className="dc-field">Message (optional)
              <input maxLength={maxMessage} value={message} placeholder="Thanks for sharing this!" onChange={(event) => setMessage(event.target.value)} />
              <small>{message.length}/{maxMessage}</small>
            </label>
            {error && <p role="alert" className="dc-error">{error}</p>}
            <button className="dc-btn dc-btn-primary dc-btn-block" disabled={!valid || busy} onClick={() => void send()}>
              {step === 'wallet' ? 'Confirm in your wallet…' : `Send ${valid ? amount : ''} ETH`}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
