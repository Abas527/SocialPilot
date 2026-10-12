import { useMemo, useState } from 'react'
import { PageHeading } from '../components/PageHeading'
import type { ProjectDetail } from '../types'

type SourcesPageProps = {
  project: ProjectDetail
  loading: boolean
  onAnalyze: () => void
}

export function SourcesPage({ project, loading, onAnalyze }: SourcesPageProps) {
  const [query, setQuery] = useState('')
  const documents = useMemo(
    () => (project.documents ?? []).filter((document) =>
      document.path.toLowerCase().includes(query.trim().toLowerCase()),
    ),
    [project.documents, query],
  )

  return (
    <div className="sources-page">
      <PageHeading
        eyebrow="SOURCE LIBRARY"
        title="The facts behind the story."
        subtitle="SocialPilot uses your project sources to keep generated content grounded and verifiable."
      />
      <div className="source-summary panel">
        <div className="source-count"><span>◫</span><div><strong>{project.documents?.length ?? 0}</strong><small>source documents</small></div></div>
        <div className="source-details"><strong>{project.name}</strong><p>{project.repository_url || 'Private work sample'} · indexed for source-grounded insights</p></div>
        <button className="button button-secondary" onClick={onAnalyze} disabled={loading}>
          {loading ? 'Analyzing…' : 'Re-analyze sources'}
        </button>
      </div>
      <div className="source-list panel">
        <div className="source-list-heading">
          <div><span className="panel-kicker">INDEXED FILES</span><h2>Project materials</h2></div>
          <span className="source-file-count">{documents.length} of {project.documents?.length ?? 0} files</span>
        </div>
        <label className="source-search-label">
          <span className="sr-only">Filter source files by path</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter files by path…" />
        </label>
        {documents.length ? documents.map((document) => (
          <div className="source-row" key={document.source_id}>
            <span className="file-icon">▤</span>
            <div>
              <strong>{document.path}</strong>
              <small>{document.content.length.toLocaleString()} characters</small>
              <details className="source-preview">
                <summary>Preview source text</summary>
                <pre>{document.content}</pre>
              </details>
            </div>
            <span className="indexed-label"><i /> Indexed</span>
            {document.source_url && <a className="source-origin-link" href={document.source_url} target="_blank" rel="noreferrer">Original ↗</a>}
          </div>
        )) : <div className="empty-sources">{query ? 'No source paths match that filter.' : 'No project sources were found.'}</div>}
      </div>
    </div>
  )
}
