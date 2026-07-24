import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { StatusBadge } from '../../components/StatusBadge/StatusBadge'
import { Drawer } from '../../components/Drawer/Drawer'
import { JsonGrid } from '../../components/JsonGrid/JsonGrid'
import { jobService } from '../../services/jobService'
import {
  extractTicketKey,
  formatAssignee,
  formatDate,
  getTimeline,
} from '../../lib/jobs/jobs'
import type { JobDetail } from '../../types/job'
import './JobDetailPage.scss'

export function JobDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [detail, setDetail] = useState<JobDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [contextOpen, setContextOpen] = useState(false)
  const [openArtifacts, setOpenArtifacts] = useState<Set<number>>(new Set())

  // Unblock form state
  const [unblockOpen, setUnblockOpen] = useState(false)
  const [unblockReason, setUnblockReason] = useState('')
  const [unblockSubmitting, setUnblockSubmitting] = useState(false)
  const [unblockError, setUnblockError] = useState<string | null>(null)

  const toggleArtifact = (index: number) => {
    setOpenArtifacts((prev) => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  useEffect(() => {
    if (!id) return
    const numId = Number(id)
    if (Number.isNaN(numId)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- early-exit error state for invalid ID
      setError('Invalid job ID')
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    jobService.fetchJobDetail(numId)
      .then((d) => {
        if (cancelled) return
        setDetail(d)
        if (!d) setError('Job not found')
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load job')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id])

  /**
   * Submit the unblock form. Validates that the reason is non-empty before
   * calling the API. On success, refreshes the job detail and closes the
   * drawer. On error, displays a user-friendly message.
   */
  async function handleUnblockSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!detail) return

    const trimmed = unblockReason.trim()
    if (!trimmed) {
      setUnblockError('Please provide an unblock reason.')
      return
    }

    setUnblockSubmitting(true)
    setUnblockError(null)

    try {
      await jobService.unblockJob(detail.id, trimmed)

      // Refresh the job detail to reflect the new status and fields.
      const refreshed = await jobService.fetchJobDetail(detail.id)
      if (refreshed) setDetail(refreshed)

      // Reset form state and close the drawer.
      setUnblockOpen(false)
      setUnblockReason('')
    } catch (err) {
      setUnblockError(
        err instanceof Error
          ? err.message
          : 'Failed to unblock job. Please try again.',
      )
    } finally {
      setUnblockSubmitting(false)
    }
  }

  /** Open the unblock drawer and reset form state. */
  function openUnblockForm() {
    setUnblockReason('')
    setUnblockError(null)
    setUnblockOpen(true)
  }

  if (loading) {
    return <div className="ff-detail">Loading job…</div>
  }

  if (error || !detail) {
    return (
      <div className="ff-detail">
        <p className="ff-detail__error">{error ?? 'Job not found'}</p>
        <Link to="/jobs" className="ff-detail__back">
          ← Back to jobs
        </Link>
      </div>
    )
  }

  const ticket = extractTicketKey(detail.summary)
  const timeline = getTimeline(detail)

  return (
    <div className="ff-detail">
      <button
        type="button"
        className="ff-detail__back"
        onClick={() => navigate('/jobs')}
      >
        ← Back to jobs
      </button>

      {/* Header */}
      <div className="ff-detail__header">
        <div className="ff-detail__header-left">
          <h1 className="ff-detail__title">{detail.summary}</h1>
          {ticket && (
            <span className="ff-detail__ticket">{ticket}</span>
          )}
        </div>
        <div className="ff-detail__header-right">
          <StatusBadge status={detail.status} />
          <span className="ff-detail__priority">Priority {detail.priority}</span>
          {detail.status === 'blocked' && (
            <button
              type="button"
              className="ff-detail__unblock-btn"
              onClick={openUnblockForm}
            >
              Unblock
            </button>
          )}
        </div>
      </div>

      {/* Metadata grid */}
      <div className="ff-detail__grid">
        <div className="ff-detail__field">
          <span className="ff-detail__label">Job ID</span>
          <span className="ff-detail__value">#{detail.id}</span>
        </div>
        <div className="ff-detail__field">
          <span className="ff-detail__label">Source Agent</span>
          <span className="ff-detail__value ff-detail__value--mono">
            {detail.source_agent_label}
          </span>
        </div>
        <div className="ff-detail__field">
          <span className="ff-detail__label">Assignee</span>
          <span className="ff-detail__value ff-detail__value--mono">
            {formatAssignee(detail.assignee_agent_label)}
          </span>
        </div>
        <div className="ff-detail__field">
          <span className="ff-detail__label">Target Role</span>
          <span className="ff-detail__value">
            {detail.target_role_label}
          </span>
        </div>
        {detail.parent_job_id && (
          <div className="ff-detail__field">
            <span className="ff-detail__label">Parent Job</span>
            <Link
              to={`/jobs/${detail.parent_job_id}`}
              className="ff-detail__value ff-detail__value--link"
            >
              {detail.parent_job_summary}
            </Link>
          </div>
        )}
        <div className="ff-detail__field">
          <span className="ff-detail__label">Context</span>
          <a
            href="#"
            className="ff-detail__value ff-detail__value--link"
            onClick={(e) => {
              e.preventDefault()
              setContextOpen(true)
            }}
          >
            details
          </a>
        </div>
        <div className="ff-detail__field">
          <span className="ff-detail__label">Created</span>
          <span className="ff-detail__value">
            {formatDate(detail.created_at)}
          </span>
        </div>
        <div className="ff-detail__field">
          <span className="ff-detail__label">Updated</span>
          <span className="ff-detail__value">
            {formatDate(detail.updated_at)}
          </span>
        </div>
      </div>

      {/* Failure / blocked / unblocked reason callouts */}
      {detail.failure_reason && (
        <div className="ff-detail__callout ff-detail__callout--danger">
          <strong>Failure Reason:</strong> {detail.failure_reason}
        </div>
      )}
      {detail.blocked_reason && (
        <div className="ff-detail__callout ff-detail__callout--warning">
          <strong>Blocked Reason:</strong> {detail.blocked_reason}
        </div>
      )}
      {detail.status === 'unblocked' && detail.unblock_reason && (
        <div className="ff-detail__callout ff-detail__callout--info">
          <strong>Unblock Reason:</strong> {detail.unblock_reason}
          {detail.unblocked_at && (
            <span className="ff-detail__callout-meta">
              {' '}(unblocked {formatDate(detail.unblocked_at)})
            </span>
          )}
        </div>
      )}

      {/* Constraints */}
      {detail.constraints.length > 0 && (
        <section className="ff-detail__section">
          <h2>Constraints</h2>
          {detail.constraints.map((c) => (
            <p key={c}>
              <span className="ff-detail__constraint">{c}</span>
            </p>
          ))}
        </section>
      )}

      {/* Artifacts */}
      {detail.artifacts.length > 0 && (
        <section className="ff-detail__section">
          <h2>Artifacts</h2>
          <div className="ff-detail__artifacts">
            {detail.artifacts.map((a, i) => (
              <div key={i} className="ff-detail__artifact">
                <button
                  type="button"
                  className="ff-detail__artifact-header"
                  aria-expanded={openArtifacts.has(i)}
                  onClick={() => toggleArtifact(i)}
                >
                  <span className="ff-detail__value--mono">{a.type}</span>
                  <span className="ff-detail__value--mono">{a.uri}</span>
                  <span
                    className="ff-detail__artifact-chevron"
                    aria-hidden="true"
                  />
                </button>
                {a.checksum && (
                  <div className="ff-detail__artifact-checksum ff-detail__value--mono">
                    {a.checksum}
                  </div>
                )}
                {openArtifacts.has(i) && <JsonGrid data={a.metadata_json} />}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Timeline */}
      <section className="ff-detail__section">
        <h2>Timeline</h2>
        <div className="ff-detail__timeline">
          {timeline.map((event, i) => (
            <div key={i} className="ff-detail__timeline-item">
              <div className="ff-detail__timeline-dot" />
              <div className="ff-detail__timeline-content">
                <span className="ff-detail__timeline-label">
                  {event.label}
                </span>
                <span className="ff-detail__timeline-time">
                  {formatDate(event.timestamp)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Context payload drawer */}
      <Drawer
        open={contextOpen}
        onClose={() => setContextOpen(false)}
        title="Context Payload"
        width="75%"
      >
        <JsonGrid data={detail.context_payload} />
      </Drawer>

      {/* Unblock form drawer */}
      <Drawer
        open={unblockOpen}
        onClose={() => setUnblockOpen(false)}
        title="Unblock Job"
        width="500px"
      >
        <form className="ff-detail__unblock-form" onSubmit={handleUnblockSubmit}>
          <p className="ff-detail__unblock-desc">
            Provide a reason for unblocking this job. The job will transition
            from <strong>Blocked</strong> to <strong>Unblocked</strong>.
          </p>
          <label className="ff-detail__unblock-label" htmlFor="unblock-reason">
            Unblock Reason <span className="ff-detail__required">*</span>
          </label>
          <textarea
            id="unblock-reason"
            className="ff-detail__unblock-textarea"
            value={unblockReason}
            onChange={(e) => setUnblockReason(e.target.value)}
            placeholder="e.g. Dependency resolved, environment is now available…"
            rows={4}
            disabled={unblockSubmitting}
            autoFocus
          />
          {unblockError && (
            <p className="ff-detail__unblock-error">{unblockError}</p>
          )}
          <div className="ff-detail__unblock-actions">
            <button
              type="button"
              className="ff-detail__unblock-cancel"
              onClick={() => setUnblockOpen(false)}
              disabled={unblockSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="ff-detail__unblock-submit"
              disabled={unblockSubmitting}
            >
              {unblockSubmitting ? 'Unblocking…' : 'Confirm Unblock'}
            </button>
          </div>
        </form>
      </Drawer>
    </div>
  )
}
