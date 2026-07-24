import type { JobStatus } from '../../types/job'
import './StatusBadge.scss'

const STATUS_VARIANT: Record<JobStatus, string> = {
  published: 'ff-badge--info',
  claimed: 'ff-badge--info',
  in_progress: 'ff-badge--primary',
  completed: 'ff-badge--success',
  blocked: 'ff-badge--warning',
  failed: 'ff-badge--danger',
  cancelled: 'ff-badge--neutral',
}

const STATUS_LABEL: Record<JobStatus, string> = {
  published: 'Published',
  claimed: 'Claimed',
  in_progress: 'In Progress',
  completed: 'Completed',
  blocked: 'Blocked',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

interface StatusBadgeProps {
  status: JobStatus
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`ff-badge ${STATUS_VARIANT[status]}`}>
      {STATUS_LABEL[status]}
    </span>
  )
}
