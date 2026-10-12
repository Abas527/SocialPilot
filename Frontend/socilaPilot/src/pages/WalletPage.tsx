import { useEffect, useState } from 'react'
import { ArrowDownLeft, ArrowUpRight, BadgeCheck, ExternalLink, ShieldCheck, WalletCards } from 'lucide-react'
import { PageHeading } from '../components/PageHeading'
import { api } from '../services/api'
import type { CreatorProfile, PreparedTip, WalletProvider } from '../types'

type ReceivedTip = {
  tip_id: string
  tx_hash: string
  amount_wei: string
  sender_username: string
  verified_at: string
  network: string
  status: 'verified'
}

const SEPOLIA_CHAIN = '0xaa36a7'
const WEI_PER_ETH = 10n ** 18n

function loadWalletData(): Promise<[CreatorProfile, ReceivedTip[]]> {
  return Promise.all([
    api<CreatorProfile>('/social/profile'),
    api<ReceivedTip[]>('/tips/received'),
  ])
}

function formatEth(value: bigint): string {
  const whole = value / WEI_PER_ETH
  const fraction = (value % WEI_PER_ETH).toString().padStart(18, '0').slice(0, 5)
  return `${whole}.${fraction}`.replace(/\.?0+$/, '')
}

function shortAddress(address: string): string {
  return `${address.slice(0, 6)}…${address.slice(-4)}`
}

export function WalletPage({ initialTab = 'account' }: { initialTab?: 'account' | 'send' | 'activity' }) {
  const [activeTab, setActiveTab] = useState<'account' | 'send' | 'activity'>(initialTab)
  const [profile, setProfile] = useState<CreatorProfile | null>(null)
  const [received, setReceived] = useState<ReceivedTip[]>([])
  const [balance, setBalance] = useState('')
  const [balanceMessage, setBalanceMessage] = useState('')
  const [recipient, setRecipient] = useState('')
  const [amount, setAmount] = useState('0.001')
  const [preparedTip, setPreparedTip] = useState<PreparedTip | null>(null)
  const [txHash, setTxHash] = useState('')
  const [busy, setBusy] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const loadWallet = async () => {
    const [account, tips] = await loadWalletData()
    setProfile(account)
    setReceived(tips)
    setLoading(false)
  }

  useEffect(() => {
    let active = true
    const initialize = async () => {
      try {
        const [account, tips] = await loadWalletData()
        if (!active) return
        setProfile(account)
        setReceived(tips)
      } catch (cause: unknown) {
        if (active) setError(cause instanceof Error ? cause.message : 'Could not load wallet details.')
      } finally {
        if (active) setLoading(false)
      }
    }
    void initialize()
    return () => { active = false }
  }, [])

  useEffect(() => {
    const refreshBalance = async () => {
      const address = profile?.wallet_address
      const provider: WalletProvider | undefined = window.ethereum
      if (!address || !provider) return
      try {
        const chain = await provider.request({ method: 'eth_chainId' })
        if (chain !== SEPOLIA_CHAIN) {
          setBalanceMessage('Switch your wallet to Sepolia to view its test ETH balance.')
          return
        }
        const result = await provider.request({
          method: 'eth_getBalance',
          params: [address, 'latest'],
        })
        if (typeof result !== 'string' || !/^0x[0-9a-f]+$/i.test(result)) {
          throw new Error('Wallet returned an invalid balance.')
        }
        setBalance(formatEth(BigInt(result)))
        setBalanceMessage('')
      } catch (cause: unknown) {
        setBalanceMessage(cause instanceof Error ? cause.message : 'Could not read Sepolia balance.')
      }
    }
    void refreshBalance()
  }, [profile?.wallet_address])

  const run = async (label: string, action: () => Promise<void>) => {
    setBusy(label)
    setError('')
    setNotice('')
    try {
      await action()
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : 'The wallet request could not be completed.')
    } finally {
      setBusy('')
    }
  }

  const verifyWallet = () => run('wallet', async () => {
    const provider: WalletProvider | undefined = window.ethereum
    if (!provider) throw new Error('Install an EVM wallet such as MetaMask to link a wallet.')
    const accounts = await provider.request({ method: 'eth_requestAccounts' })
    if (!Array.isArray(accounts) || typeof accounts[0] !== 'string') {
      throw new Error('No wallet account was selected.')
    }
    const address = accounts[0]
    const challenge = await api<{ challenge_id: string; message: string }>('/wallet/challenge', {
      method: 'POST',
      body: JSON.stringify({ address }),
    })
    const signature = await provider.request({
      method: 'personal_sign',
      params: [challenge.message, address],
    })
    if (typeof signature !== 'string') throw new Error('Wallet did not return a signature.')
    await api('/wallet/verify', {
      method: 'POST',
      body: JSON.stringify({ challenge_id: challenge.challenge_id, signature }),
    })
    await loadWallet()
    setNotice('Wallet ownership verified with a message signature. No transaction was sent.')
  })

  const prepareTip = () => run('prepare', async () => {
    const tip = await api<PreparedTip>('/tips/prepare', {
      method: 'POST',
      body: JSON.stringify({ recipient_username: recipient.trim(), amount_eth: amount }),
    })
    setPreparedTip(tip)
    setTxHash('')
    setNotice(`Review the ${tip.asset} transfer to @${recipient.trim()} in your wallet.`)
  })

  const sendTip = () => run('send', async () => {
    const provider: WalletProvider | undefined = window.ethereum
    if (!provider) throw new Error('Install an EVM wallet such as MetaMask to send a tip.')
    if (!preparedTip) throw new Error('Prepare a tip before sending it.')
    let chain = await provider.request({ method: 'eth_chainId' })
    if (chain !== SEPOLIA_CHAIN) {
      await provider.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: SEPOLIA_CHAIN }],
      })
      chain = await provider.request({ method: 'eth_chainId' })
    }
    if (chain !== SEPOLIA_CHAIN) throw new Error('Switch your wallet to Sepolia to continue.')
    const accounts = await provider.request({ method: 'eth_requestAccounts' })
    if (!Array.isArray(accounts) || typeof accounts[0] !== 'string') {
      throw new Error('No wallet account was selected.')
    }
    if (accounts[0].toLowerCase() !== preparedTip.from.toLowerCase()) {
      throw new Error('The connected wallet does not match your verified sender wallet.')
    }
    const sent = await provider.request({
      method: 'eth_sendTransaction',
      params: [{
        from: preparedTip.from,
        to: preparedTip.to,
        value: preparedTip.value,
        chainId: SEPOLIA_CHAIN,
      }],
    })
    if (typeof sent !== 'string') throw new Error('Wallet did not return a transaction hash.')
    setTxHash(sent)
    setNotice('Tip submitted to Sepolia. Verify it after it is mined.')
  })

  const verifyTip = () => run('verify', async () => {
    if (!preparedTip || !txHash) throw new Error('Send the prepared tip before verifying it.')
    const result = await api<{ tx_hash: string }>(`/tips/${preparedTip.intent_id}/verify`, {
      method: 'POST',
      body: JSON.stringify({ tx_hash: txHash }),
    })
    setPreparedTip(null)
    setTxHash('')
    await loadWallet()
    setNotice(`Tip verified on Sepolia: ${result.tx_hash}`)
  })

  const totalReceived = received.reduce((total, tip) => total + BigInt(tip.amount_wei), 0n)

  return (
    <div className="creator-page wallet-page">
      <header className="wallet-page-header">
        <PageHeading
          eyebrow="YOUR FINANCIAL HUB"
          title="Creator wallet"
          subtitle="Connect your wallet, support creators, and keep track of every verified tip."
        />
        <span className="wallet-network-pill"><span /> Sepolia testnet</span>
      </header>
      {error && <p role="alert" className="wallet-feedback wallet-error">{error}</p>}
      {notice && <p role="status" className="wallet-feedback wallet-success">{notice}</p>}

      <div className="wallet-tabs" role="tablist" aria-label="Wallet sections">
        <button id="wallet-tab-account" type="button" role="tab" aria-controls="wallet-panel-account" aria-selected={activeTab === 'account'} onClick={() => setActiveTab('account')}>Wallet &amp; balance</button>
        <button id="wallet-tab-send" type="button" role="tab" aria-controls="wallet-panel-send" aria-selected={activeTab === 'send'} onClick={() => setActiveTab('send')}>Send a tip</button>
        <button id="wallet-tab-activity" type="button" role="tab" aria-controls="wallet-panel-activity" aria-selected={activeTab === 'activity'} onClick={() => setActiveTab('activity')}>Tip activity <span>{received.length}</span></button>
      </div>

      {activeTab === 'account' && <div id="wallet-panel-account" role="tabpanel" aria-labelledby="wallet-tab-account" className="wallet-tab-panel">
      <section className="wallet-account-hero">
        <div className="wallet-account-main">
          <div className="wallet-account-label"><span className="wallet-account-icon"><WalletCards size={19} /></span><span>WALLET BALANCE</span></div>
          <strong className="wallet-balance-value">{profile?.wallet_address ? balance ? `${balance} ETH` : 'Balance unavailable' : 'No wallet connected'}</strong>
          <p>{profile?.wallet_address ? 'Your connected Sepolia testnet balance' : 'Connect a wallet to send tips and list products.'}</p>
          {profile?.wallet_address && (
            <div className="wallet-account-address">
              <BadgeCheck size={15} />
              <code>{profile.wallet_address}</code>
              <a aria-label="View wallet on Sepolia Etherscan" href={`https://sepolia.etherscan.io/address/${profile.wallet_address}`} target="_blank" rel="noreferrer"><ExternalLink size={15} /></a>
            </div>
          )}
          {balanceMessage && <p role="status" className="wallet-balance-message">{balanceMessage}</p>}
        </div>
        <div className="wallet-account-action">
          <span className="wallet-account-action-icon"><ShieldCheck size={22} /></span>
          <strong>{profile?.wallet_address ? 'Wallet verified' : 'Connect your wallet'}</strong>
          <p>{profile?.wallet_address
            ? 'Address ownership is confirmed. You can update it any time.'
            : 'Verify ownership with a wallet signature. SocialPilot never asks for your seed phrase.'}</p>
          <button className="wallet-connect-button" disabled={Boolean(busy) || loading} onClick={verifyWallet}>
            {busy === 'wallet' ? 'Check your wallet…' : profile?.wallet_address ? 'Verify another wallet' : 'Connect & verify'}
            {!busy && <ArrowUpRight size={16} />}
          </button>
        </div>
        <div className="wallet-hero-decoration wallet-hero-decoration-one" />
        <div className="wallet-hero-decoration wallet-hero-decoration-two" />
      </section>

      <div className="wallet-summary-grid">
        <article className="wallet-summary-card">
          <span className="wallet-summary-icon"><ArrowDownLeft size={19} /></span>
          <div><p>Total tips received</p><strong>{formatEth(totalReceived)} <small>ETH</small></strong><span>{received.length} verified {received.length === 1 ? 'tip' : 'tips'}</span></div>
        </article>
        <article className="wallet-summary-card wallet-network-card">
          <span className="wallet-summary-icon"><ShieldCheck size={19} /></span>
          <div><p>Connected network</p><strong>Sepolia</strong><span>Testnet only · no real funds</span></div>
        </article>
      </div>
      <button className="wallet-tab-next-action" onClick={() => setActiveTab('send')}><ArrowUpRight size={17} /> Send a creator tip</button>
      </div>}

      {activeTab === 'send' && <div id="wallet-panel-send" role="tabpanel" aria-labelledby="wallet-tab-send" className="wallet-tab-panel">
      <div className="wallet-content-grid">
        <section className="wallet-panel wallet-tip-panel">
          <div className="wallet-panel-heading">
            <span className="wallet-panel-icon"><ArrowUpRight size={18} /></span>
            <div><h2>Send a creator tip</h2><p>Support a builder with a direct Sepolia transfer.</p></div>
          </div>
          <div className="wallet-tip-form">
            <label>Creator username
              <input value={recipient} onChange={(event) => setRecipient(event.target.value)} placeholder="e.g. build_with_me" />
            </label>
            <label>Tip amount
              <div className="wallet-amount-field">
                <input aria-label="Tip amount in Sepolia ETH" type="number" min="0.000000000000000001" max="1" step="0.000000000000000001" value={amount} onChange={(event) => setAmount(event.target.value)} />
                <span>ETH</span>
              </div>
            </label>
            <div className="wallet-quick-amounts" aria-label="Choose a tip amount">
              {['0.001', '0.005', '0.01'].map((value) => (
                <button key={value} type="button" className={amount === value ? 'selected' : ''} onClick={() => setAmount(value)}>{value} ETH</button>
              ))}
            </div>
            {!profile?.wallet_address && <p className="wallet-inline-note">Connect and verify your wallet before preparing a tip.</p>}
            <button className="wallet-send-button" disabled={Boolean(busy) || loading || !profile?.wallet_address || !recipient.trim()} onClick={prepareTip}>
              {busy === 'prepare' ? 'Preparing transfer…' : 'Review tip'} <ArrowUpRight size={16} />
            </button>
          </div>
          {preparedTip && (
            <div className="wallet-transfer">
              <div><strong>Transfer ready</strong><span>{preparedTip.asset} · {preparedTip.network} · {preparedTip.expires_at ? `Expires ${new Date(preparedTip.expires_at).toLocaleTimeString()}` : 'Review in wallet'}</span></div>
              <code>{shortAddress(preparedTip.to)}</code>
              {!txHash ? (
                <button className="button button-secondary" disabled={Boolean(busy)} onClick={sendTip}>
                  {busy === 'send' ? 'Confirm in wallet…' : 'Send with wallet'}
                </button>
              ) : (
                <>
                  <a href={`https://sepolia.etherscan.io/tx/${txHash}`} target="_blank" rel="noreferrer">{shortAddress(txHash)} <ExternalLink size={13} /></a>
                  <button className="button button-primary" disabled={Boolean(busy)} onClick={verifyTip}>
                    {busy === 'verify' ? 'Verifying…' : 'Verify transaction'}
                  </button>
                </>
              )}
            </div>
          )}
          <p className="wallet-risk-note"><ShieldCheck size={15} /> Transfers are irreversible. Confirm the creator and amount in your wallet. Use test ETH only.</p>
        </section>

        <section className="wallet-panel wallet-how-panel">
          <div className="wallet-panel-heading">
            <span className="wallet-panel-icon"><ShieldCheck size={18} /></span>
            <div><h2>Protected by design</h2><p>Know exactly what happens before anything is sent.</p></div>
          </div>
          <ol className="wallet-safety-steps">
            <li><span>01</span><div><strong>Prepare</strong><p>Choose a creator and an amount to create a transfer request.</p></div></li>
            <li><span>02</span><div><strong>Review in your wallet</strong><p>Your wallet shows the recipient and amount before you approve.</p></div></li>
            <li><span>03</span><div><strong>Verify on-chain</strong><p>SocialPilot checks Sepolia before adding the tip to your history.</p></div></li>
          </ol>
          <p className="wallet-safety-footnote">Wallet signatures prove ownership only. Never share your seed phrase or private key.</p>
        </section>
      </div>
      </div>}

      {activeTab === 'activity' && <div id="wallet-panel-activity" role="tabpanel" aria-labelledby="wallet-tab-activity" className="wallet-tab-panel">
      <section className="wallet-panel wallet-history">
        <div className="wallet-panel-heading wallet-history-heading">
          <span className="wallet-panel-icon"><ArrowDownLeft size={18} /></span>
          <div><span className="community-section-kicker">ON-CHAIN ACTIVITY</span><h2>Tip history</h2><p>Only transfers verified on Sepolia appear here.</p></div>
          <span className="wallet-history-count">{received.length} {received.length === 1 ? 'tip' : 'tips'}</span>
        </div>
        {loading ? (
          <p className="wallet-empty">Loading wallet activity…</p>
        ) : received.length === 0 ? (
          <div className="wallet-empty">
            <span className="wallet-empty-icon"><ArrowDownLeft size={20} /></span>
            <strong>No tips in your history yet</strong>
            <p>Tips you receive will show up here after their Sepolia transaction is verified.</p>
          </div>
        ) : (
          <div className="wallet-activity-list">
            {received.map((tip) => (
              <article className="wallet-activity-row" key={tip.tip_id}>
                <span className="wallet-activity-icon"><ArrowDownLeft size={16} /></span>
                <div className="wallet-activity-detail">
                  <strong>Tip from @{tip.sender_username}</strong>
                  <span>{new Date(tip.verified_at).toLocaleString()} · {tip.network}</span>
                </div>
                <strong className="wallet-activity-amount">+{formatEth(BigInt(tip.amount_wei))} ETH</strong>
                <a aria-label="View transaction on Sepolia Etherscan" href={`https://sepolia.etherscan.io/tx/${tip.tx_hash}`} target="_blank" rel="noreferrer">
                  <ExternalLink size={15} />
                </a>
              </article>
            ))}
          </div>
        )}
      </section>
      </div>}
    </div>
  )
}
