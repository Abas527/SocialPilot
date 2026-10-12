import type { EvidenceClaim } from '../types'

export function ClaimSummary({ claims }: { claims: EvidenceClaim[] }) {
  if (!claims.length) return null

  const supported = claims.filter((claim) => claim.status === 'supported').length
  const needsReview = claims.length - supported

  return (
    <div className="claims-box">
      <div className="claims-heading">
        <span className="claims-check">✓</span>
        <div>
          <strong>Evidence check</strong>
          <small>Draft claims compared with project sources</small>
        </div>
        <b>{supported}/{claims.length}</b>
      </div>
      <div className="claim-badges">
        <span className="supported-badge">✓ {supported} supported</span>
        {needsReview > 0 && <span className="review-badge">! {needsReview} need review</span>}
      </div>
      {claims.slice(0, 4).map((claim, index) => (
        <div className="claim-row" key={`${claim.text}-${index}`}>
          <span className={`claim-status ${claim.status === 'supported' ? 'good' : 'caution'}`}>
            {claim.status === 'supported' ? '✓' : '!'}
          </span>
          <div>
            <p>{claim.text}</p>
            {claim.evidence?.[0] ? (
              <>
                <small>
                  {claim.evidence[0].source_url ? (
                    <a href={claim.evidence[0].source_url} target="_blank" rel="noreferrer">
                      {claim.evidence[0].path}{claim.evidence[0].start_line ? `:${claim.evidence[0].start_line}` : ''}
                    </a>
                  ) : `${claim.evidence[0].path}${claim.evidence[0].start_line ? `:${claim.evidence[0].start_line}` : ''}`}
                </small>
                {claim.evidence[0].excerpt && <blockquote>{claim.evidence[0].excerpt}</blockquote>}
              </>
            ) : <small>{claim.note || 'No supporting source found'}</small>}
          </div>
        </div>
      ))}
    </div>
  )
}
