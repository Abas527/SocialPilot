import { CheckCircle2, Loader2, X, XCircle } from 'lucide-react'
import { useJobs } from './JobsProvider'

/** Floating list of running and recently finished AI jobs, with live progress. */
export function JobsTray() {
  const { jobs, cancel, dismiss, labels } = useJobs()
  if (!jobs.length) return null
  return (
    <aside className="dc-jobs" aria-label="AI tasks" aria-live="polite">
      {jobs.slice(0, 4).map((job) => {
        const active = job.status === 'queued' || job.status === 'running'
        return (
          <div key={job.job_id} className={`dc-job dc-job-${job.status}`}>
            <div className="dc-job-head">
              {active ? <Loader2 size={15} className="dc-spin" aria-hidden="true" />
                : job.status === 'succeeded' ? <CheckCircle2 size={15} aria-hidden="true" />
                : <XCircle size={15} aria-hidden="true" />}
              <strong>{labels[job.job_id] ?? 'AI task'}</strong>
              {active
                ? <button type="button" onClick={() => void cancel(job.job_id)}>Cancel</button>
                : <button type="button" onClick={() => dismiss(job.job_id)} aria-label="Dismiss"><X size={14} /></button>}
            </div>
            {active ? (
              <>
                <div className="dc-progress" role="progressbar" aria-valuenow={job.progress} aria-valuemin={0} aria-valuemax={100}>
                  <span style={{ width: `${Math.max(6, job.progress)}%` }} />
                </div>
                <small>{job.step || 'Working'}… {job.progress}%</small>
              </>
            ) : (
              <small>{job.status === 'succeeded' ? 'Finished' : job.status === 'cancelled' ? 'Cancelled' : job.error ?? 'Failed'}</small>
            )}
          </div>
        )
      })}
    </aside>
  )
}
