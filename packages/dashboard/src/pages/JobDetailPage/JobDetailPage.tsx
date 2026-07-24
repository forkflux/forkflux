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

      {/* Failure / blocked reason callouts */}
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
    </div>
  )
}
