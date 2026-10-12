import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { InfiniteData, QueryClient } from '@tanstack/react-query'
import {
  PAGE_SIZE, addComment, createPost, deleteComment, deletePost, editPost, fetchPosts, getComments,
  getMyProfile, getNotifications, getPost, getPostTips, getProfile, markAllRead, searchProfiles,
  setBookmark, setFollow, setLike, suggestedProfiles, trendingTags, unreadCount,
} from '../services/community'
import type { FeedParams, NewPost } from '../services/community'
import type { CreatorProfile, Post } from '../types'

export function useInfinitePosts(params: FeedParams) {
  return useInfiniteQuery({
    queryKey: ['posts', params],
    queryFn: ({ pageParam }) => fetchPosts(params, pageParam),
    initialPageParam: 0,
    getNextPageParam: (last, all) => (last.length < PAGE_SIZE ? undefined : all.length * PAGE_SIZE),
  })
}

export const usePost = (id: string) => useQuery({ queryKey: ['post', id], queryFn: () => getPost(id) })
export const useComments = (id: string) => useQuery({ queryKey: ['comments', id], queryFn: () => getComments(id) })
export const usePostTips = (id: string, enabled: boolean) =>
  useQuery({ queryKey: ['post-tips', id], queryFn: () => getPostTips(id), enabled })
export const useMyProfile = () => useQuery({ queryKey: ['profile', 'me'], queryFn: getMyProfile, staleTime: 60_000 })
export const useProfile = (username: string) =>
  useQuery({ queryKey: ['profile', username], queryFn: () => getProfile(username) })
export const useTrendingTags = () => useQuery({ queryKey: ['trending-tags'], queryFn: trendingTags, staleTime: 120_000 })
export const useSuggestedProfiles = () =>
  useQuery({ queryKey: ['suggested-profiles'], queryFn: () => suggestedProfiles(5), staleTime: 60_000 })
export const usePeopleSearch = (q: string) =>
  useQuery({ queryKey: ['people-search', q], queryFn: () => searchProfiles(q), enabled: q.trim().length > 0 })
export const useNotifications = () => useQuery({ queryKey: ['notifications'], queryFn: getNotifications })
export const useUnreadCount = () =>
  useQuery({ queryKey: ['unread'], queryFn: unreadCount, refetchInterval: 30_000 })

/** Apply `fn` to a post wherever it is cached (every feed page and the detail view). */
export function patchPostCaches(qc: QueryClient, postId: string, fn: (post: Post) => Post) {
  qc.setQueriesData<InfiniteData<Post[]>>({ queryKey: ['posts'] }, (data) =>
    data && { ...data, pages: data.pages.map((page) => page.map((post) => (post.post_id === postId ? fn(post) : post))) })
  qc.setQueryData<Post>(['post', postId], (post) => (post ? fn(post) : post))
}

export function useLikeMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ post, on }: { post: Post; on: boolean }) => setLike(post.post_id, on),
    onMutate: ({ post, on }) => {
      patchPostCaches(qc, post.post_id, (p) => ({
        ...p, liked_by_me: on, like_count: Math.max(0, p.like_count + (on ? 1 : -1)),
      }))
    },
    onError: (_error, { post, on }) => {
      patchPostCaches(qc, post.post_id, (p) => ({
        ...p, liked_by_me: !on, like_count: Math.max(0, p.like_count + (on ? -1 : 1)),
      }))
    },
  })
}

export function useBookmarkMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ post, on }: { post: Post; on: boolean }) => setBookmark(post.post_id, on),
    onMutate: ({ post, on }) => patchPostCaches(qc, post.post_id, (p) => ({ ...p, bookmarked_by_me: on })),
    onError: (_error, { post, on }) => patchPostCaches(qc, post.post_id, (p) => ({ ...p, bookmarked_by_me: !on })),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['posts'], predicate: (q) => Boolean((q.queryKey[1] as { bookmarks?: boolean })?.bookmarks) }) },
  })
}

export function useCreatePost() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (post: NewPost) => createPost(post),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['posts'] })
      void qc.invalidateQueries({ queryKey: ['trending-tags'] })
    },
  })
}

export function useEditPost() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: { body?: string; tags?: string[] } }) => editPost(id, patch),
    onSuccess: (post) => patchPostCaches(qc, post.post_id, () => post),
  })
}

export function useDeletePost() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deletePost(id),
    onSuccess: (_void, id) => {
      qc.setQueriesData<InfiniteData<Post[]>>({ queryKey: ['posts'] }, (data) =>
        data && { ...data, pages: data.pages.map((page) => page.filter((post) => post.post_id !== id)) })
      qc.removeQueries({ queryKey: ['post', id] })
    },
  })
}

export function useAddComment(postId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: string) => addComment(postId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['comments', postId] })
      patchPostCaches(qc, postId, (p) => ({ ...p, comment_count: p.comment_count + 1 }))
    },
  })
}

export function useDeleteComment(postId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (commentId: string) => deleteComment(commentId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['comments', postId] })
      patchPostCaches(qc, postId, (p) => ({ ...p, comment_count: Math.max(0, p.comment_count - 1) }))
    },
  })
}

export function useFollowMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ username, on }: { username: string; on: boolean }) => setFollow(username, on),
    onSuccess: (_result, { username, on }) => {
      const apply = (p: CreatorProfile): CreatorProfile =>
        p.username === username
          ? { ...p, is_following: on, follower_count: Math.max(0, p.follower_count + (on ? 1 : -1)) }
          : p
      qc.setQueryData<CreatorProfile>(['profile', username], (p) => (p ? apply(p) : p))
      qc.setQueriesData<CreatorProfile[]>({ queryKey: ['suggested-profiles'] }, (list) => list?.map(apply))
      qc.setQueriesData<CreatorProfile[]>({ queryKey: ['people-search'] }, (list) => list?.map(apply))
      qc.setQueriesData<CreatorProfile[]>({ queryKey: ['follows'] }, (list) => list?.map(apply))
      qc.setQueriesData<InfiniteData<Post[]>>({ queryKey: ['posts'] }, (data) =>
        data && { ...data, pages: data.pages.map((page) => page.map((post) =>
          post.author.username === username
            ? { ...post, author: { ...post.author, is_following: on } }
            : post)) })
      void qc.invalidateQueries({ queryKey: ['posts'], predicate: (q) => (q.queryKey[1] as FeedParams)?.scope === 'following' })
    },
  })
}

export function useMarkAllRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: markAllRead,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['notifications'] })
      qc.setQueryData(['unread'], { unread: 0 })
    },
  })
}
