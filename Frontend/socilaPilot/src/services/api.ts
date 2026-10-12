import type { CaseStudy, ExportFormat, LinkedInDraft } from '../types'

const API_BASE = import.meta.env.VITE_API_URL ?? ''
const ACCESS_TOKEN_KEY = 'socialpilot_access_token'
let accessToken = sessionStorage.getItem(ACCESS_TOKEN_KEY)

function formatApiError(body: string, status: number): string {
  const fallback = `Request failed (${status})`
  if (!body) return fallback

  try {
    const parsed: unknown = JSON.parse(body)
    if (typeof parsed !== 'object' || parsed === null || !('detail' in parsed)) {
      return body
    }

    const { detail } = parsed
    if (typeof detail === 'string' && detail.trim()) return detail
    if (Array.isArray(detail)) {
      const messages = detail.flatMap((item) => {
        if (typeof item !== 'object' || item === null || !('msg' in item)) return []
        const message = item.msg
        if (typeof message !== 'string' || !message.trim()) return []

        const locationParts: unknown[] = 'loc' in item && Array.isArray(item.loc) ? item.loc : []
        const location = locationParts.filter((part): part is string | number =>
            (typeof part === 'string' || typeof part === 'number') && part !== 'body'
              && part !== 'query' && part !== 'path' && part !== 'header')
        const field = location.map(String).join('.').replaceAll('_', ' ')
        return [field ? `${field}: ${message}` : message]
      })
      if (messages.length) return messages.join(' ')
    }
    if (typeof detail === 'number' || typeof detail === 'boolean') return String(detail)
  } catch {
    return body
  }

  return fallback
}

let onUnauthorized: (() => void) | null = null

/** Called when an authenticated request comes back 401 (expired or revoked session). */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler
}

export function hasAccessToken(): boolean {
  return Boolean(accessToken)
}

export function setAccessToken(token: string | null): void {
  accessToken = token
  if (token) sessionStorage.setItem(ACCESS_TOKEN_KEY, token)
  else sessionStorage.removeItem(ACCESS_TOKEN_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (!headers.has('Content-Type') && init?.body) {
    headers.set('Content-Type', 'application/json')
  }
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  })
  if (!response.ok) {
    if (response.status === 401 && accessToken && !path.startsWith('/auth/login')) {
      setAccessToken(null)
      onUnauthorized?.()
    }
    throw new ApiError(formatApiError(await response.text(), response.status), response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function exportCaseStudy(
  format: ExportFormat,
  caseStudy: CaseStudy,
  repositoryUrl: string | null,
): Promise<Blob> {
  const path = format === 'pdf' ? '/export/pdf' : '/export/markdown'
  const response = await fetch(
    `${API_BASE}${path}?repo_url=${encodeURIComponent(repositoryUrl ?? '')}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: JSON.stringify(caseStudy),
    },
  )
  if (!response.ok) {
    throw new Error(formatApiError(await response.text(), response.status))
  }
  return response.blob()
}

export function downloadFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export function caseStudyFilename(caseStudy: CaseStudy, format: ExportFormat): string {
  const slug = caseStudy.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')
  return `${slug}.${format === 'pdf' ? 'pdf' : 'md'}`
}

export function saveLinkedInDraft(projectId: string, angle: string, content: LinkedInDraft): Promise<{ saved: boolean }> {
  return api(`/projects/${projectId}/artifacts/linkedin:${angle}`, {
    method: 'PUT',
    body: JSON.stringify(content),
  })
}

export function saveCaseStudy(projectId: string, content: CaseStudy): Promise<{ saved: boolean }> {
  return api(`/projects/${projectId}/artifacts/case_study`, {
    method: 'PUT',
    body: JSON.stringify(content),
  })
}
