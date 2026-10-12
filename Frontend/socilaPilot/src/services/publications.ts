import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import type {
  OwnershipStart, OwnershipStatus, Post, PublicPublication, PublicationSummary, ReverifyResult,
} from '../types'

export type ShareResult = { post: Post; publication: { publication_id: string; supported: number; total: number; trust_level: 'repository' | 'notes'; ownership_verified: boolean } }

export const publicationKeys = {
  list: (projectId: string) => ['publications', projectId] as const,
  ownership: (projectId: string) => ['ownership', projectId] as const,
  public: (id: string) => ['public-publication', id] as const,
}

export function usePublications(projectId: string) {
  return useQuery({ queryKey: publicationKeys.list(projectId), queryFn: () => api<PublicationSummary[]>(`/projects/${projectId}/publications`) })
}

export function useOwnership(projectId: string, enabled = true) {
  return useQuery({ queryKey: publicationKeys.ownership(projectId), enabled, queryFn: () => api<OwnershipStatus>(`/projects/${projectId}/ownership`) })
}

export function useShareCaseStudy(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: { note: string; tags: string[] }) =>
      api<ShareResult>(`/projects/${projectId}/share/case-study`, { method: 'POST', body: JSON.stringify(input) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: publicationKeys.list(projectId) })
      void qc.invalidateQueries({ queryKey: ['posts'] })
    },
  })
}

export function useCreateEvidencePage(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api<{ publication_id: string }>(`/projects/${projectId}/publications/case-study`, { method: 'POST' }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: publicationKeys.list(projectId) }),
  })
}

export function useUnpublish(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (publicationId: string) => api<void>(`/publications/${publicationId}`, { method: 'DELETE' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: publicationKeys.list(projectId) })
      void qc.invalidateQueries({ queryKey: ['posts'] })
    },
  })
}

export function useStartOwnership(projectId: string) {
  return useMutation({ mutationFn: () => api<OwnershipStart>(`/projects/${projectId}/ownership/start`, { method: 'POST' }) })
}

export function useCheckOwnership(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api<OwnershipStatus>(`/projects/${projectId}/ownership/check`, { method: 'POST' }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: publicationKeys.ownership(projectId) }),
  })
}

/** Public: no login needed. */
export function usePublicPublication(id: string) {
  return useQuery({ queryKey: publicationKeys.public(id), retry: false, queryFn: () => api<PublicPublication>(`/public/publications/${id}`) })
}

export function reverifyPublication(id: string): Promise<ReverifyResult> {
  return api<ReverifyResult>(`/public/publications/${id}/reverify`, { method: 'POST' })
}
