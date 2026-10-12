import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  AlertTriangle, BadgeCheck, CircleHelp, ExternalLink, FileSearch, GitCommitHorizontal, Hash, Moon,
  ShieldAlert, ShieldCheck, Sun,
} from 'lucide-react'
import { Markdown } from '../components/Markdown'
import { Avatar, Spinner } from '../components/community/bits'
import { errorMessage, fullDate } from '../lib/format'
import { reverifyPublication, usePublicPublication } from '../services/publications'
import { useAppTheme } from '../theme/ThemeContext'
import type { PublicClaim, PublicPublication, ReverifyResult } from '../types'

const SECTION_TITLES: Record<string, string> = {
  summary: 'Summary', problem: 'Problem', architecture: 'Architecture', implementation: 'Implementation',
  challenges: 'Challenges', results: 'Results', limitations: 'Limitations', future_work: 'Future work', body: 'Post',
}
const SECTION_ORDER = ['summary', 'problem', 'architecture', 'implementation', 'challenges', 'results', 'limitations', 'future_work']

type Check = ReverifyResult['claims'][number]['status']
const CHECK_LABEL: Record<Check, string> = {
  confirmed: 'Re-checked on GitHub ✓', mismatch: 'Not found at that commit', unreachable: 'Could not reach GitHub', no_evidence: 'No source matched',
}

function ClaimRow({ claim, check }: { claim: PublicClaim; check?: Check }) {
  const [open, setOpen] = useState(false)
  const ok = claim.status === 'supported'
  return (
    <li className={`dc-claim ${ok ? 'is-supported' : 'is-unmatched'}`}>
      <button className="dc-claim-head" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        {ok ? <BadgeCheck size={16} aria-hidden="true" /> : <CircleHelp size={16} aria-hidden="true" />}
        <span className="dc-claim-text">{claim.text}</span>
        {check && <span className={`dc-claim-check dc-check-${check}`}>{CHECK_LABEL[check]}</span>}
      </button>
      {open && (
        <div className="dc-claim-body">
          {claim.evidence.length === 0 && <p className="dc-muted">No excerpt in the author's sources matched this statement. Treat it as the author's own claim.</p>}
          {claim.evidence.map((ev, index) => (
            <figure key={`${ev.path}:${ev.start_line}:${index}`} className="dc-excerpt">
              <figcaption>
                <code>{ev.path}{ev.start_line != null ? `:${ev.start_line}${ev.end_line && ev.end_line !== ev.start_line ? `–${ev.end_line}` : ''}` : ''}</code>
                {ev.permalink && <a href={ev.permalink} target="_blank" rel="noopener noreferrer">View on GitHub <ExternalLink size={12} aria-hidden="true" /></a>}
              </figcaption>
              <blockquote>{ev.excerpt}</blockquote>
            </figure>
          ))}
        </div>
      )}
    </li>
  )
}

function TrustPanel({ data, onVerify, verifying, result, verifyError }: {
  data: PublicPublication; onVerify: () => void; verifying: boolean; result: ReverifyResult | null; verifyError: string
}) {
  const { trust, integrity } = data
  const repo = trust.repository
  const repoBacked = trust.level === 'repository'
  return (
    <section className={`dc-trust ${repoBacked ? 'is-repo' : 'is-notes'}`} aria-label="How much to trust this">
      <div className="dc-trust-head">
        {repoBacked ? <ShieldCheck size={22} aria-hidden="true" /> : <ShieldAlert size={22} aria-hidden="true" />}
        <div>
          <h2>{repoBacked ? 'Repository-backed' : 'Self-reported'}</h2>
          <p>{trust.label}</p>
        </div>
      </div>
      <dl className="dc-trust-facts">
        <div><dt>Statements matched to sources</dt><dd>{trust.supported} of {trust.total}</dd></div>
        {repo && (
          <div>
            <dt>Repository</dt>
            <dd><a href={repo.url} target="_blank" rel="noopener noreferrer">{repo.owner}/{repo.name} <ExternalLink size={12} aria-hidden="true" /></a></dd>
          </div>
        )}
        {repo?.commit_sha && (
          <div>
            <dt>Pinned commit</dt>
            <dd><a href={repo.commit_url ?? undefined} target="_blank" rel="noopener noreferrer"><GitCommitHorizontal size={13} aria-hidden="true" /> <code>{repo.commit_sha.slice(0, 10)}</code></a></dd>
          </div>
        )}
        {repoBacked && (
          <div>
            <dt>Repository owner</dt>
            <dd>{trust.ownership_verified
              ? <span className="dc-ok"><BadgeCheck size={14} aria-hidden="true" /> Verified: the author proved control of this repository</span>
              : <span className="dc-warn-text"><AlertTriangle size={14} aria-hidden="true" /> Not verified: the author has not proved they own this repository</span>}</dd>
          </div>
        )}
        <div>
          <dt>Unchanged since published</dt>
          <dd>{integrity.intact
            ? <span className="dc-ok"><Hash size={13} aria-hidden="true" /> Yes · sha256 <code title={integrity.content_sha256}>{integrity.content_sha256.slice(0, 16)}…</code></span>
            : <span className="dc-warn-text">Hash mismatch: this content no longer matches what was published</span>}</dd>
        </div>
      </dl>
      {repoBacked && (
        <div className="dc-trust-actions">
          <button className="dc-btn dc-btn-primary" onClick={onVerify} disabled={verifying}>
            <FileSearch size={15} aria-hidden="true" /> {verifying ? 'Checking GitHub…' : 'Re-check the evidence on GitHub'}
          </button>
          <span className="dc-muted">Downloads each cited file at the pinned commit and confirms the excerpt is really there.</span>
        </div>
      )}
      {verifyError && <p role="alert" className="dc-error">{verifyError}</p>}
      {result && (() => {
        const states = result.claims.map((c) => c.status).filter((st) => st !== 'no_evidence')
        const unreachable = states.length > 0 && states.every((st) => st === 'unreachable')
        if (unreachable) return <p role="status" className="dc-warn-text">GitHub could not be reached, so nothing was checked. Try again in a moment.</p>
        const good = result.confirmed === result.checked && result.checked > 0
        return (
          <p role="status" className={good ? 'dc-ok' : 'dc-warn-text'}>
            {result.confirmed} of {result.checked} supported statements confirmed against GitHub at {result.commit_sha.slice(0, 10)}.
            {!good && result.checked > 0 && ' Some excerpts could not be found at that commit. Open each statement to see which.'}
          </p>
        )
      })()}
      <details className="dc-method">
        <summary>How is this checked, and what it does not prove</summary>
        <p>{trust.method}</p>
        <p>It cannot tell you the claim is correct, that the code works, or that the author wrote it
          {trust.ownership_verified ? '' : ' (repository ownership has not been verified)'}. Use it to see where each statement comes from, then judge for yourself.</p>
      </details>
    </section>
  )
}

export function PublicationPage() {
  const { publicationId = '' } = useParams()
  const { theme, toggle } = useAppTheme()
  const query = usePublicPublication(publicationId)
  const [result, setResult] = useState<ReverifyResult | null>(null)
  const [verifying, setVerifying] = useState(false)
  const [verifyError, setVerifyError] = useState('')
  const data = query.data

  const verify = async () => {
    setVerifying(true); setVerifyError('')
    try { setResult(await reverifyPublication(publicationId)) } catch (cause) { setVerifyError(errorMessage(cause)) } finally { setVerifying(false) }
  }

  const checks = new Map(result?.claims.map((c) => [c.index, c.status]))
  const sectionsPresent = data ? SECTION_ORDER.filter((key) => data.content[key]?.trim()) : []
  const claimsBySection = new Map<string, { claim: PublicClaim; index: number }[]>()
  data?.claims.forEach((claim, index) => {
    const list = claimsBySection.get(claim.section) ?? []
    list.push({ claim, index }); claimsBySection.set(claim.section, list)
  })

  return (
    <div className="dc-public" data-theme={theme}>
      <header className="dc-public-bar">
        <Link to="/" className="dc-public-brand">social<span>pilot</span></Link>
        <div className="dc-row">
          <button className="dc-icon-btn" onClick={toggle} aria-label="Toggle theme">{theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}</button>
          <Link className="dc-btn" to="/login">Sign in</Link>
        </div>
      </header>
      <main className="dc-public-main">
        {query.isLoading && <Spinner label="Loading evidence…" />}
        {query.isError && (
          <div className="dc-card" role="alert">
            <h1>This page is not available</h1>
            <p className="dc-muted">{errorMessage(query.error)}</p>
          </div>
        )}
        {data && (
          <>
            <p className="dc-kicker">{data.kind === 'case_study' ? 'CASE STUDY' : 'POST'} · EVIDENCE PASSPORT</p>
            <h1 className="dc-public-title">{data.title || 'Post'}</h1>
            <p className="dc-public-by">
              <Avatar name={data.author.display_name} size={26} /> {data.author.display_name} <span className="dc-handle">@{data.author.username}</span>
              <span className="dc-dot">·</span> published {fullDate(data.created_at)}
            </p>

            <TrustPanel data={data} onVerify={() => void verify()} verifying={verifying} result={result} verifyError={verifyError} />

            <article className="dc-card dc-public-content" aria-label="Published content">
              {data.kind === 'post'
                ? <Markdown>{data.content.body ?? ''}</Markdown>
                : sectionsPresent.map((key) => (
                  <section key={key}>
                    <h2>{SECTION_TITLES[key]}</h2>
                    <p className="dc-prewrap">{data.content[key]}</p>
                  </section>
                ))}
            </article>

            <section className="dc-card" aria-label="Evidence by statement">
              <h2>Evidence, statement by statement</h2>
              <p className="dc-muted">Open a statement to see the source text it was matched to. Statements without a match are the author's own claims.</p>
              {data.claims.length === 0 && <p className="dc-muted">No checkable statements were found in this text.</p>}
              {[...claimsBySection.entries()].map(([section, rows]) => (
                <div key={section} className="dc-claim-group">
                  {data.kind === 'case_study' && <h3>{SECTION_TITLES[section] ?? section}</h3>}
                  <ul className="dc-claims">{rows.map(({ claim, index }) => <ClaimRow key={index} claim={claim} check={checks.get(index)} />)}</ul>
                </div>
              ))}
            </section>

            {data.sources.length > 0 && (
              <section className="dc-card" aria-label="Source files">
                <h2>Source files used</h2>
                <ul className="dc-sources">
                  {data.sources.map((s) => (
                    <li key={s.path}>
                      {s.source_url ? <a href={s.source_url} target="_blank" rel="noopener noreferrer"><code>{s.path}</code></a> : <code>{s.path}</code>}
                      <code className="dc-muted" title={s.sha256}>sha256 {s.sha256.slice(0, 12)}…</code>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  )
}
