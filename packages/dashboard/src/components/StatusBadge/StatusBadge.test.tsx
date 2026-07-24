import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import { StatusBadge } from './StatusBadge'
import { renderWithRouter } from '../../test/utils'
import type { JobStatus } from '../../types/job'

const STATUS_LABELS: Record<JobStatus, string> = {
  published: 'Published',
  claimed: 'Claimed',
  in_progress: 'In Progress',
  completed: 'Completed',
  blocked: 'Blocked',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

const STATUS_VARIANTS: Record<JobStatus, string> = {
  published: 'ff-badge--info',
  claimed: 'ff-badge--info',
  in_progress: 'ff-badge--primary',
  completed: 'ff-badge--success',
  blocked: 'ff-badge--warning',
  failed: 'ff-badge--danger',
  cancelled: 'ff-badge--neutral',
}

describe('StatusBadge', () => {
  for (const status of Object.keys(STATUS_LABELS) as JobStatus[]) {
    it(`renders correct label and variant for status "${status}"`, () => {
      renderWithRouter(<StatusBadge status={status} />)
      const badge = screen.getByText(STATUS_LABELS[status])
      expect(badge).toBeInTheDocument()
      expect(badge).toHaveClass('ff-badge', STATUS_VARIANTS[status])
    })
  }
})
