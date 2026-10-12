import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowDownWideNarrow, ArrowRight, Bot, Blocks, Code2, PackageOpen, Search, ShoppingBag } from 'lucide-react'
import { PageHeading } from '../components/PageHeading'
import { api } from '../services/api'
import type { CreatorProfile, WalletProvider } from '../types'

type ProductType = 'plugin' | 'library' | 'agent'

type Listing = {
  listing_id: string
  product_type: ProductType
  title: string
  description: string
  price_wei: string
  price_eth: string
  seller: { username: string; display_name: string; is_demo: boolean }
  created_at: string
  active: boolean
}

type PreparedPurchase = {
  intent_id: string
  listing_id: string
  chain_id: number
  from: string
  to: string
  value: string
  amount_wei: string
  expires_at: string
  network: string
  asset: string
}

type Purchase = {
  sale_id: string
  listing_id: string
  title: string
  product_type: ProductType
  amount_wei: string
  tx_hash: string
  verified_at: string
  status: 'verified'
  delivery_url: string
}

const CHAIN_ID = '0xaa36a7'
const productTypes: { id: ProductType; label: string; icon: typeof Code2 }[] = [
  { id: 'plugin', label: 'Plugins', icon: Blocks },
  { id: 'library', label: 'Libraries', icon: Code2 },
  { id: 'agent', label: 'AI agents', icon: Bot },
]

export function MarketplacePage({ onOpenWallet }: { onOpenWallet: () => void }) {
  const [listings, setListings] = useState<Listing[]>([])
  const [myListings, setMyListings] = useState<Listing[]>([])
  const [purchases, setPurchases] = useState<Purchase[]>([])
  const [profile, setProfile] = useState<CreatorProfile | null>(null)
  const [productType, setProductType] = useState<ProductType | ''>('')
  const [query, setQuery] = useState('')
  const [appliedQuery, setAppliedQuery] = useState('')
  const [sortOrder, setSortOrder] = useState<'recent' | 'price-low' | 'price-high'>('recent')
  const [activeTab, setActiveTab] = useState<'explore' | 'sell' | 'library'>('explore')
  const [draft, setDraft] = useState({
    product_type: 'plugin' as ProductType,
    title: '',
    description: '',
    price_eth: '0.01',
    delivery_url: '',
  })
  const [prepared, setPrepared] = useState<PreparedPurchase | null>(null)
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null)
  const [txHash, setTxHash] = useState('')
  const [busy, setBusy] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [demoEnabled, setDemoEnabled] = useState(false)
  const sortedListings = [...listings].sort((first, second) => {
    if (sortOrder === 'price-low') return BigInt(first.price_wei) < BigInt(second.price_wei) ? -1 : BigInt(first.price_wei) > BigInt(second.price_wei) ? 1 : 0
    if (sortOrder === 'price-high') return BigInt(first.price_wei) > BigInt(second.price_wei) ? -1 : BigInt(first.price_wei) < BigInt(second.price_wei) ? 1 : 0
    return new Date(second.created_at).getTime() - new Date(first.created_at).getTime()
  })

  const loadMarketplace = useCallback(async () => {
    const params = new URLSearchParams()
    if (appliedQuery.trim()) params.set('q', appliedQuery.trim())
    if (productType) params.set('product_type', productType)
    setLoading(true)
    try {
      const [items, mine, profileData, sales] = await Promise.all([
        api<Listing[]>(`/marketplace/listings?${params.toString()}`),
        api<Listing[]>('/marketplace/mine'),
        api<CreatorProfile>('/social/profile'),
        api<Omit<Purchase, 'delivery_url'>[]>('/marketplace/purchases'),
      ])
      const purchaseDetails = await Promise.all(
        sales.map((sale) => api<Purchase>(`/marketplace/purchases/${sale.sale_id}`)),
      )
      setListings(items)
      setMyListings(mine)
      setProfile(profileData)
      setPurchases(purchaseDetails)
    } finally {
      setLoading(false)
    }
  }, [appliedQuery, productType])

  useEffect(() => {
    const initialize = async () => {
      try {
        await loadMarketplace()
        api<{ enabled: boolean }>('/demo/status').then((status) => setDemoEnabled(status.enabled)).catch(() => undefined)
      } catch (cause: unknown) {
        setError(cause instanceof Error ? cause.message : 'Could not load marketplace.')
      }
    }
    void initialize()
  }, [loadMarketplace])

  const run = async (label: string, action: () => Promise<void>) => {
    setBusy(label)
    setError('')
    setNotice('')
    try {
      await action()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The marketplace request failed.')
    } finally {
      setBusy('')
    }
  }

  const loadSampleCatalog = () => run('seed', async () => {
    const result = await api<{ creators: number; posts: number; listings: number }>('/demo/seed', { method: 'POST' })
    await loadMarketplace()
    setNotice(result.listings
      ? `Added ${result.listings} sample plugins, libraries and agents to explore. Sample tools are preview-only and cannot be bought.`
      : 'The sample catalog is already loaded.')
  })

  const createListing = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    return run('create', async () => {
      await api('/marketplace/listings', {
        method: 'POST',
        body: JSON.stringify(draft),
      })
      setDraft({ ...draft, title: '', description: '', delivery_url: '' })
      await loadMarketplace()
      setNotice('Your listing is live. Buyers receive its link only after verified payment.')
    })
  }

  const buyListing = (listing: Listing) => run(`buy:${listing.listing_id}`, async () => {
    const provider: WalletProvider | undefined = window.ethereum
    if (!provider) throw new Error('Install an EVM wallet such as MetaMask to purchase.')
    let chainId = await provider.request({ method: 'eth_chainId' })
    if (chainId !== CHAIN_ID) {
      await provider.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: CHAIN_ID }],
      })
      chainId = await provider.request({ method: 'eth_chainId' })
    }
    if (chainId !== CHAIN_ID) throw new Error('Switch your wallet to Sepolia to continue.')
    const accounts = await provider.request({ method: 'eth_requestAccounts' })
    if (!Array.isArray(accounts) || typeof accounts[0] !== 'string') {
      throw new Error('No wallet account was selected.')
    }
    if (!profile?.wallet_address || accounts[0].toLowerCase() !== profile.wallet_address.toLowerCase()) {
      throw new Error('Connected wallet does not match your verified buyer wallet.')
    }
    const intent = await api<PreparedPurchase>(
      `/marketplace/listings/${listing.listing_id}/purchase`,
      { method: 'POST' },
    )
    setPrepared(intent)
    setTxHash('')
    if (accounts[0].toLowerCase() !== intent.from.toLowerCase()) {
      throw new Error('Connected wallet does not match your verified buyer wallet.')
    }
    const sent = await provider.request({
      method: 'eth_sendTransaction',
      params: [{ from: intent.from, to: intent.to, value: intent.value, chainId: CHAIN_ID }],
    })
    if (typeof sent !== 'string') throw new Error('Wallet did not return a transaction hash.')
    setTxHash(sent)
    setNotice('Payment sent to the creator on Sepolia. Verify it after it is mined.')
  })

  const verifyPurchase = () => run('verify', async () => {
    if (!prepared || !txHash) throw new Error('Send the prepared payment before verifying.')
    await api(`/marketplace/purchases/${prepared.intent_id}/verify`, {
      method: 'POST',
      body: JSON.stringify({ tx_hash: txHash }),
    })
    setPrepared(null)
    setTxHash('')
    await loadMarketplace()
    setNotice('Payment verified. Your buyer-only download link is now available below.')
  })

  const deactivateListing = (listingId: string) => run(`deactivate:${listingId}`, async () => {
    await api(`/marketplace/listings/${listingId}`, { method: 'DELETE' })
    await loadMarketplace()
    setNotice('Listing removed from the marketplace. Existing buyers keep their access.')
  })

  const search = () => run('search', async () => {
    setAppliedQuery(query)
  })

  const confirmPurchase = () => {
    if (!selectedListing) return
    const listing = selectedListing
    setSelectedListing(null)
    void buyListing(listing)
  }

  return (
    <div className="creator-page marketplace-page">
      <header className="marketplace-titlebar">
        <PageHeading eyebrow="CREATOR MARKETPLACE" title="Tools made by builders." subtitle="Explore independent developer tools, manage your listings, and find purchases." />
      </header>
      {error && <p role="alert" className="rounded-lg border border-rose-400/20 bg-rose-400/5 p-3 text-sm text-rose-200">{error}</p>}
      {notice && <p role="status" className="rounded-lg border border-emerald-300/20 bg-emerald-300/5 p-3 text-sm text-emerald-200">{notice}</p>}

      <div className="marketplace-overview">
        <article><span className="marketplace-overview-icon"><PackageOpen size={17} /></span><div><strong>{listings.length}</strong><span>Tools to explore</span></div></article>
        <article><span className="marketplace-overview-icon"><Blocks size={17} /></span><div><strong>{myListings.filter((item) => item.active).length}</strong><span>Your active listings</span></div></article>
        <article><span className="marketplace-overview-icon"><ShoppingBag size={17} /></span><div><strong>{purchases.length}</strong><span>Verified purchases</span></div></article>
      </div>

      <div className="creator-tabs" role="tablist" aria-label="Marketplace sections">
        {([
          ['explore', 'Explore tools'],
          ['sell', 'Sell your work'],
          ['library', 'My library'],
        ] as const).map(([tab, label]) => (
          <button
            key={tab}
            role="tab"
            aria-selected={activeTab === tab}
            aria-controls={`marketplace-${tab}`}
            id={`marketplace-tab-${tab}`}
            className={activeTab === tab ? 'selected' : ''}
            onClick={() => setActiveTab(tab)}
          >
            {label}
            {tab === 'library' && <span>{purchases.length}</span>}
          </button>
        ))}
      </div>

      {activeTab === 'explore' && <section id="marketplace-explore" role="tabpanel" aria-labelledby="marketplace-tab-explore" className="marketplace-explore marketplace-section">
        <div className="marketplace-toolbar">
          <div className="marketplace-toolbar-title"><span className="marketplace-section-kicker">FIND YOUR NEXT FAVORITE TOOL</span><h2>Explore the marketplace</h2><p>Independent tools and ideas from the community.</p></div>
          <form className="marketplace-search" onSubmit={(event) => { event.preventDefault(); void search() }}>
            <Search size={17} aria-hidden="true" />
            <label className="sr-only" htmlFor="marketplace-search">Search listings</label>
            <input id="marketplace-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tools, libraries, agents…" />
            <button type="submit" disabled={Boolean(busy)}>Search</button>
          </form>
        </div>
        <div className="marketplace-filter-row">
          <div className="marketplace-category-filters" aria-label="Filter by product category">
            <button className={productType === '' ? 'selected' : ''} onClick={() => setProductType('')}>All tools</button>
            {productTypes.map(({ id, label, icon: Icon }) => (
              <button key={id} className={productType === id ? 'selected' : ''} onClick={() => setProductType(id)}><Icon size={14} /> {label}</button>
            ))}
          </div>
          <label className="marketplace-sort"><ArrowDownWideNarrow size={15} /><span>Sort</span>
            <select value={sortOrder} onChange={(event) => {
              const value = event.target.value
              if (value === 'recent' || value === 'price-low' || value === 'price-high') setSortOrder(value)
            }}>
              <option value="recent">Recently added</option>
              <option value="price-low">Price: low to high</option>
              <option value="price-high">Price: high to low</option>
            </select>
          </label>
        </div>

        <div className="marketplace-results-heading">
          <span>{loading ? 'Loading tools…' : `${listings.length} ${listings.length === 1 ? 'tool' : 'tools'} available`}</span>
          {(appliedQuery || productType) && <button onClick={() => { setQuery(''); setAppliedQuery(''); setProductType('') }}>Clear filters</button>}
        </div>
        {demoEnabled && !loading && !appliedQuery && !productType && !listings.some((item) => item.seller.is_demo) && (
          <div className="marketplace-sample-banner" role="note">
            <span><strong>Want something to browse?</strong> Load a sample catalog of plugins, libraries and AI agents. Sample tools are labelled and cannot be purchased.</span>
            <button type="button" className="button button-secondary" onClick={() => void loadSampleCatalog()} disabled={Boolean(busy)}>
              {busy === 'seed' ? 'Loading…' : 'Load sample catalog'}
            </button>
          </div>
        )}
        <div className="marketplace-product-grid">
          {!loading && sortedListings.map((item) => {
            const ProductIcon = productTypes.find(({ id }) => id === item.product_type)?.icon ?? Code2
            return (
            <article key={item.listing_id} className="marketplace-product-card">
              <div className="marketplace-product-art"><ProductIcon size={23} /><span>{item.product_type}</span></div>
              <div className="marketplace-product-meta">
                <span className={`marketplace-product-kind kind-${item.product_type}`}>{item.product_type}</span>
                {item.seller.is_demo && <span className="marketplace-demo-label">Sample</span>}
                <span className="marketplace-product-price">{item.price_eth}<small> Sepolia ETH</small></span>
              </div>
              <h3>{item.title}</h3>
              <p className="marketplace-product-description">{item.description}</p>
              <div className="marketplace-product-seller"><span>{item.seller.display_name.trim().charAt(0).toUpperCase()}</span><div><strong>{item.seller.display_name}</strong><small>@{item.seller.username}{item.seller.is_demo ? ' · Sample creator' : ''}</small></div></div>
              <button disabled={Boolean(busy) || item.seller.is_demo || !profile?.wallet_address || item.seller.username === profile.username} onClick={() => setSelectedListing(item)} className="marketplace-buy-button">
                {item.seller.is_demo ? 'Sample tool · preview only' : busy === `buy:${item.listing_id}` ? 'Waiting for wallet…' : !profile?.wallet_address ? 'Verify a wallet first' : item.seller.username === profile.username ? 'Your listing' : 'Buy with Sepolia ETH'}
                {!item.seller.is_demo && profile?.wallet_address && item.seller.username !== profile.username && <ArrowRight size={15} />}
              </button>
            </article>
          )})}
          {loading && <p role="status" className="text-sm text-slate-500">Loading creator products…</p>}
          {!loading && listings.length === 0 && (
            <div className="marketplace-empty-state">
              <span className="marketplace-empty-icon"><PackageOpen size={23} /></span>
              <div>
                <span className="panel-kicker">{appliedQuery || productType ? 'NO MATCHES YET' : 'BUILT BY THE COMMUNITY'}</span>
                <h2>{appliedQuery || productType ? 'No products match those filters.' : 'Give your next developer tool a home.'}</h2>
                <p>{appliedQuery || productType
                  ? 'Try another search or clear the filters to browse every active listing.'
                  : 'Publish a plugin, library, or agent with a clear description and a seller-hosted delivery link.'}</p>
              </div>
              <button
                className="button button-secondary"
                onClick={() => {
                  if (appliedQuery || productType) {
                    setQuery('')
                    setAppliedQuery('')
                    setProductType('')
                  } else {
                    setActiveTab('sell')
                  }
                }}
              >
                {appliedQuery || productType ? 'Clear filters' : 'Create a listing'}
                <ArrowRight size={15} />
              </button>
            </div>
          )}
        </div>
      </section>}

      {prepared && txHash && (
        <section className="rounded-xl border border-amber-200/20 bg-amber-200/[0.04] p-5">
          <p className="text-sm font-semibold text-amber-100">Payment submitted</p>
          <p className="mt-2 break-all font-mono text-xs text-slate-400">{txHash}</p>
          <button disabled={Boolean(busy)} onClick={verifyPurchase} className="mt-3 rounded-lg bg-amber-200 px-4 py-2 text-xs font-semibold text-slate-950 disabled:opacity-50">
            {busy === 'verify' ? 'Checking confirmations…' : 'Verify payment & unlock'}
          </button>
        </section>
      )}

      {activeTab === 'sell' && <div id="marketplace-sell" role="tabpanel" className="grid gap-6 lg:grid-cols-2">
        <section id="marketplace-sell-form" className="rounded-xl border border-white/10 bg-[#101827] p-5 marketplace-section">
          <h2 className="text-sm font-semibold text-white">Sell something you built</h2>
          <p className="mt-1 text-xs leading-5 text-slate-500">Provide a seller-hosted HTTPS delivery URL. SocialPilot returns it only to verified buyers, but your hosting provider controls whether the URL itself can be shared. Direct wallet transfers are not escrowed or refundable by SocialPilot.</p>
          {!profile?.wallet_address && <p className="mt-3 text-xs text-amber-200">Link and verify a wallet before listing. <button type="button" onClick={onOpenWallet} className="underline underline-offset-2">Open Wallet</button></p>}
          <form onSubmit={createListing} className="mt-4 space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-slate-400">Type
                <select value={draft.product_type} onChange={(event) => {
                  const selected = productTypes.find(({ id }) => id === event.target.value)
                  if (selected) setDraft({ ...draft, product_type: selected.id })
                }} className="mt-1.5 block w-full rounded-lg border border-white/10 bg-[#0a101d] px-3 py-2.5 text-sm text-white">
                  {productTypes.map(({ id, label }) => <option key={id} value={id}>{label}</option>)}
                </select>
              </label>
              <label className="text-xs text-slate-400">Price (Sepolia ETH)
                <input required inputMode="decimal" value={draft.price_eth} onChange={(event) => setDraft({ ...draft, price_eth: event.target.value })} className="mt-1.5 block w-full rounded-lg border border-white/10 bg-[#0a101d] px-3 py-2.5 text-sm text-white" />
              </label>
            </div>
            <label className="block text-xs text-slate-400">Name
              <input required maxLength={100} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} className="mt-1.5 w-full rounded-lg border border-white/10 bg-[#0a101d] px-3 py-2.5 text-sm text-white" />
            </label>
            <label className="block text-xs text-slate-400">What does it do?
              <textarea required maxLength={2000} rows={3} value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} className="mt-1.5 w-full resize-y rounded-lg border border-white/10 bg-[#0a101d] px-3 py-2.5 text-sm text-white" />
            </label>
            <label className="block text-xs text-slate-400">Seller-hosted HTTPS delivery URL
              <input required type="url" value={draft.delivery_url} onChange={(event) => setDraft({ ...draft, delivery_url: event.target.value })} placeholder="https://…" className="mt-1.5 w-full rounded-lg border border-white/10 bg-[#0a101d] px-3 py-2.5 text-sm text-white" />
            </label>
            <button disabled={Boolean(busy) || !profile?.wallet_address} className="rounded-lg bg-indigo-300 px-4 py-2.5 text-xs font-semibold text-slate-950 disabled:opacity-50">
              {busy === 'create' ? 'Publishing…' : 'Publish listing'}
            </button>
          </form>
        </section>

        <section className="space-y-6">
          <article className="rounded-xl border border-white/10 bg-[#101827] p-5">
            <h2 className="text-sm font-semibold text-white">Your listings</h2>
            <div className="mt-3 space-y-3">
              {myListings.length === 0 && <p className="text-xs text-slate-500">Your products will appear here.</p>}
              {myListings.map((item) => (
                <div key={item.listing_id} className="flex items-center justify-between gap-3 rounded-lg border border-white/[0.07] p-3">
                  <div><strong className="block text-xs text-slate-100">{item.title}</strong><span className="text-[11px] text-slate-500">{item.product_type} · {item.price_eth} ETH · {item.active ? 'live' : 'inactive'}</span></div>
                  {item.active && <button disabled={Boolean(busy)} onClick={() => deactivateListing(item.listing_id)} className="text-xs text-rose-200 disabled:opacity-50">Remove</button>}
                </div>
              ))}
            </div>
          </article>

        </section>
      </div>}

      {activeTab === 'library' && (
        <section className="rounded-xl border border-white/10 bg-[#101827] p-5">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div><h2 className="text-sm font-semibold text-white">Your buyer library</h2><p className="mt-1 text-xs text-slate-500">Private download links are shown only after the payment is verified.</p></div>
            <span className="text-xs text-slate-500">{purchases.length} verified {purchases.length === 1 ? 'purchase' : 'purchases'}</span>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {purchases.length === 0 && <p className="text-xs text-slate-500">Your verified purchases and buyer-only links will appear here.</p>}
            {purchases.map((purchase) => (
              <div key={purchase.sale_id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/[0.07] p-4">
                <div><strong className="block text-xs text-slate-100">{purchase.title}</strong><span className="text-[11px] text-slate-500">{purchase.product_type} · verified on Sepolia</span></div>
                <a href={purchase.delivery_url} target="_blank" rel="noreferrer" className="rounded-md border border-emerald-200/20 px-3 py-1.5 text-[11px] text-emerald-100">Open download ↗</a>
              </div>
            ))}
          </div>
        </section>
      )}

      {selectedListing && (
        <div className="marketplace-dialog-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) setSelectedListing(null) }}>
          <section className="marketplace-dialog" role="dialog" aria-modal="true" aria-labelledby="purchase-confirm-title">
            <p className="panel-kicker">REVIEW TESTNET PURCHASE</p>
            <h2 id="purchase-confirm-title">{selectedListing.title}</h2>
            <p>{selectedListing.description}</p>
            <dl>
              <div><dt>Creator</dt><dd>{selectedListing.seller.display_name} (@{selectedListing.seller.username})</dd></div>
              <div><dt>Amount</dt><dd>{selectedListing.price_eth} Sepolia ETH</dd></div>
              <div><dt>Payment</dt><dd>Directly to creator wallet · Sepolia testnet</dd></div>
            </dl>
            <p className="marketplace-dialog-warning">Only continue if you trust this creator. Payments are direct, not escrowed, and SocialPilot cannot reverse or refund them. Test ETH has no mainnet value.</p>
            <div className="marketplace-dialog-actions">
              <button type="button" disabled={Boolean(busy)} onClick={() => setSelectedListing(null)}>Cancel</button>
              <button type="button" disabled={Boolean(busy)} onClick={confirmPurchase}>{busy === `buy:${selectedListing.listing_id}` ? 'Waiting for wallet…' : 'Continue to wallet'}</button>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
