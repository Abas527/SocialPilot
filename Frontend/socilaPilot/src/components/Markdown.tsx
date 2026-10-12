import { Children, isValidElement, useState } from 'react'
import type { ComponentPropsWithoutRef, ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { Check, Copy } from 'lucide-react'

function textOf(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textOf).join('')
  if (isValidElement<{ children?: ReactNode }>(node)) return textOf(node.props.children)
  return ''
}

function CodeBlock({ children }: { children?: ReactNode }) {
  const [copied, setCopied] = useState(false)
  const code = textOf(Children.toArray(children)).replace(/\n$/, '')
  const child = Children.toArray(children)[0]
  const className = isValidElement<{ className?: string }>(child) ? child.props.className ?? '' : ''
  const language = /language-([\w+#-]+)/.exec(className)?.[1]
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch { /* clipboard unavailable */ }
  }
  return (
    <div className="dc-code">
      <div className="dc-code-bar">
        <span>{language ?? 'code'}</span>
        <button type="button" onClick={copy} aria-label="Copy code">
          {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre>{children}</pre>
    </div>
  )
}

function SafeLink(props: ComponentPropsWithoutRef<'a'>) {
  return <a {...props} target="_blank" rel="noopener noreferrer nofollow ugc" />
}

/** Markdown for user content: GitHub-flavoured, syntax-highlighted, no raw HTML, no remote images. */
export function Markdown({ children, className = '' }: { children: string; className?: string }) {
  return (
    <div className={`dc-markdown ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: false, ignoreMissing: true }]]}
        components={{
          a: SafeLink,
          pre: CodeBlock,
          img: ({ alt, src }) => (src ? <a href={src} target="_blank" rel="noopener noreferrer nofollow ugc">{alt || src}</a> : null),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
