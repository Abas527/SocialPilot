import { api } from './api'
import type {
  AppNotification, ChainConfig, CreatorProfile, Post, PostComment, PostTip, TrendingTag,
} from '../types'

export const PAGE_SIZE = 15

export type FeedParams = {
  scope?: 'following' | 'discover' | 'all'
  sort?: 'new' | 'top'
  tag?: string
  author?: string
  bookmarks?: boolean
}

export function fetchPosts(params: FeedParams, offset: number, limit = PAGE_SIZE): Promise<Post[]> {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (params.bookmarks) return api<Post[]>(`/social/bookmarks?${query}`)
  if (params.author) {
    return api<Post[]>(`/social/profiles/${encodeURIComponent(params.author)}/posts?${query}`)
  }
  query.set('scope', params.scope ?? 'all')
  query.set('sort', params.sort ?? 'new')
  if (params.tag) query.set('tag', params.tag)
  return api<Post[]>(`/social/posts?${query}`)
}

export type NewPost = {
  body: string
  format: 'plain' | 'markdown'
  tags: string[]
  link_url?: string | null
  project_id?: string | null
  artifact_ref?: string | null
}

export const createPost = (post: NewPost) =>
  api<Post>('/social/posts', { method: 'POST', body: JSON.stringify(post) })
export const editPost = (id: string, patch: { body?: string; tags?: string[] }) =>
  api<Post>(`/social/posts/${id}`, { method: 'PUT', body: JSON.stringify(patch) })
export const deletePost = (id: string) => api<void>(`/social/posts/${id}`, { method: 'DELETE' })
export const getPost = (id: string) => api<Post>(`/social/posts/${id}`)

export const setLike = (id: string, on: boolean) =>
  api<{ liked: boolean; like_count: number }>(`/social/posts/${id}/like`, { method: on ? 'POST' : 'DELETE' })
export const setBookmark = (id: string, on: boolean) =>
  api<{ bookmarked: boolean }>(`/social/posts/${id}/bookmark`, { method: on ? 'POST' : 'DELETE' })

export const getComments = (id: string) => api<PostComment[]>(`/social/posts/${id}/comments?limit=50`)
export const addComment = (id: string, body: string) =>
  api<PostComment>(`/social/posts/${id}/comments`, { method: 'POST', body: JSON.stringify({ body }) })
export const deleteComment = (commentId: string) =>
  api<void>(`/social/comments/${commentId}`, { method: 'DELETE' })

export const getPostTips = (id: string) => api<PostTip[]>(`/social/posts/${id}/tips?limit=20`)

export const getMyProfile = () => api<CreatorProfile>('/social/profile')
export const getProfile = (username: string) =>
  api<CreatorProfile>(`/social/profiles/${encodeURIComponent(username)}`)
export const searchProfiles = (q: string, limit = 20) =>
  api<CreatorProfile[]>(`/social/profiles?${new URLSearchParams({ q, limit: String(limit) })}`)
export const suggestedProfiles = (limit = 5) =>
  api<CreatorProfile[]>(`/social/profiles?limit=${limit}`)
export const getFollows = (username: string, kind: 'followers' | 'following') =>
  api<CreatorProfile[]>(`/social/profiles/${encodeURIComponent(username)}/${kind}?limit=50`)
export const setFollow = (username: string, on: boolean) =>
  api<{ following: boolean }>(`/social/follow/${encodeURIComponent(username)}`, { method: on ? 'POST' : 'DELETE' })

export type ProfilePatch = Partial<{
  username: string
  display_name: string
  bio: string
  skills: string[]
  timezone: string
  availability: CreatorProfile['availability']
}>
export const updateProfile = (patch: ProfilePatch) =>
  api<CreatorProfile>('/social/profile', { method: 'PUT', body: JSON.stringify(patch) })

export const trendingTags = () => api<TrendingTag[]>('/social/trending/tags?limit=8')

export const getNotifications = () => api<AppNotification[]>('/notifications?limit=50')
export const unreadCount = () => api<{ unread: number }>('/notifications/unread-count')
export const markAllRead = () =>
  api<{ marked: number }>('/notifications/read', { method: 'POST', body: JSON.stringify({}) })

export const chainConfig = () => api<ChainConfig>('/config/chain')
