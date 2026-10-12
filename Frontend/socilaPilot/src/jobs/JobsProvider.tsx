import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import type { AiJob, JobKind } from '../types'

export type JobRequest = { kind: JobKind; project_id?: string } & Record<string, unknown>

type RunOptions<R> = {
  /** Short label shown in the jobs tray. */
  label: string
  onProgress?: (job: AiJob<R>) => void
}

type JobsState = {
  jobs: AiJob[]
  /** Start a job and resolve with the finished job; rejects if it fails or is cancelled. */
  run: <R = unknown>(request: JobRequest, options: RunOptions<R>) => Promise<AiJob<R>>
  cancel: (jobId: string) => Promise<void>
  dismiss: (jobId: string) => void
  labels: Record<string, string>
}

const JobsContext = createContext<JobsState | null>(null)
const POLL_MS = 1000
const TERMINAL = new Set(['succeeded', 'failed', 'cancelled'])

export class JobFailedError extends Error {
  job: AiJob
  constructor(job: AiJob) {
    super(job.status === 'cancelled' ? 'The AI job was cancelled.' : job.error || 'The AI job failed.')
    this.name = 'JobFailedError'
    this.job = job
  }
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export function JobsProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [jobs, setJobs] = useState<AiJob[]>([])
  const [labels, setLabels] = useState<Record<string, string>>({})
  const alive = useRef(true)

  useEffect(() => {
    alive.current = true
    return () => { alive.current = false }
  }, [])

  const upsert = useCallback((job: AiJob) => {
    setJobs((current) => {
      const index = current.findIndex((item) => item.job_id === job.job_id)
      if (index === -1) return [job, ...current].slice(0, 8)
      const next = [...current]
      next[index] = job
      return next
    })
  }, [])

  const finish = useCallback((job: AiJob) => {
    if (job.project_id) {
      void queryClient.invalidateQueries({ queryKey: ['project', job.project_id] })
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
    }
  }, [queryClient])

  const poll = useCallback(async <R,>(jobId: string, onProgress?: (job: AiJob<R>) => void): Promise<AiJob<R>> => {
    let failures = 0
    for (;;) {
      await sleep(POLL_MS)
      try {
        const job = await api<AiJob<R>>(`/jobs/${jobId}`)
        failures = 0
        if (alive.current) upsert(job as AiJob)
        onProgress?.(job)
        if (TERMINAL.has(job.status)) {
          finish(job as AiJob)
          return job
        }
      } catch (cause) {
        failures += 1
        if (failures >= 5) throw cause
      }
    }
  }, [upsert, finish])

  // Resume tracking of jobs that were running when the page was reloaded.
  useEffect(() => {
    api<AiJob[]>('/jobs?active_only=true')
      .then((active) => {
        active.forEach((job) => {
          upsert(job)
          setLabels((current) => ({ ...current, [job.job_id]: current[job.job_id] ?? 'AI task' }))
          void poll(job.job_id).catch(() => undefined)
        })
      })
      .catch(() => undefined)
  }, [poll, upsert])

  const run = useCallback(async <R,>(request: JobRequest, options: RunOptions<R>): Promise<AiJob<R>> => {
    const created = await api<AiJob<R>>('/jobs', { method: 'POST', body: JSON.stringify(request) })
    upsert(created as AiJob)
    setLabels((current) => ({ ...current, [created.job_id]: options.label }))
    const done = TERMINAL.has(created.status) ? created : await poll<R>(created.job_id, options.onProgress)
    if (done.status !== 'succeeded') throw new JobFailedError(done as AiJob)
    return done
  }, [poll, upsert])

  const cancel = useCallback(async (jobId: string) => {
    const job = await api<AiJob>(`/jobs/${jobId}/cancel`, { method: 'POST' })
    upsert(job)
  }, [upsert])

  const dismiss = useCallback((jobId: string) => {
    setJobs((current) => current.filter((job) => job.job_id !== jobId))
  }, [])

  const value = useMemo(() => ({ jobs, run, cancel, dismiss, labels }), [jobs, run, cancel, dismiss, labels])
  return <JobsContext.Provider value={value}>{children}</JobsContext.Provider>
}

export function useJobs(): JobsState {
  const ctx = useContext(JobsContext)
  if (!ctx) throw new Error('useJobs must be used inside <JobsProvider>')
  return ctx
}
