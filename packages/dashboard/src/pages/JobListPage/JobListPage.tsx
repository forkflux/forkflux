import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Paginator } from '../../components/Paginator/Paginator'
import { StatusBadge } from '../../components/StatusBadge/StatusBadge'
import { useJobListParams } from '../../hooks/useJobListParams/useJobListParams'
import { formatAssignee, formatDate } from '../../lib/jobs/jobs'
import { jobService } from '../../services/jobService'
import type { Job, JobListMeta, JobSortField, StatusCount } from '../../types/job'
import './JobListPage.scss'

const SEARCH_DEBOUNCE_MS = 300

export function JobListPage() {
  const navigate = useNavigate()
  const {
    query,
    setStatus,
    setRole,
    setSearch,
    setDir,
    setSortAndDir,
    setOffset,
    setLimit,
  } = useJobListParams()

  const [jobs, setJobs] = useState<Job[]>([])
  const [total, setTotal] = useState(0)
  const [meta, setMeta] = useState<JobListMeta>({ statuses: [], roles: [] })
  const [counts, setCounts] = useState<StatusCount[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchInput, setSearchInput] = useState(query.search)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Sync the local search input when the URL `search` param changes externally
  // (back/forward navigation, clearing filters). This is an intentional
  // external-state → React-state synchronization.
  useEffect(() => {
    setSearchInput(query.search)
  }, [query.search])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      if (searchInput !== query.search) {
        setSearch(searchInput)
      }
    }, SEARCH_DEBOUNCE_MS)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput])

  const queryKey = useMemo(
    () =>
      JSON.stringify({
        status: query.status,
        role: query.role,
        search: query.search,
        sort: query.sort,
        dir: query.dir,
        limit: query.limit,
        offset: query.offset,
      }),
    [query],
  )

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([
      jobService.fetchJobs(query),
      jobService.fetchListMeta(query),
      jobService.fetchJobCounts(),
    ])
      .then(([res, metaRes, countsRes]) => {
        if (cancelled) return
        setJobs(res.items)
        setTotal(res.total)
        setMeta(metaRes)
        setCounts(countsRes)
        setError(null)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load jobs')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryKey])

  function toggleSort(field: JobSortField) {
    if (query.sort === field) {
      setDir(query.dir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortAndDir(field, 'asc')
    }
  }

  if (loading) {
    return <div className="ff-jobs">Loading jobs…</div>
  }

  if (error) {
    return <div className="ff-jobs ff-jobs--error">Error: {error}</div>
  }

  const { roles: distinctRoles } = meta

  return (
    <div className="ff-jobs">
      <div className="ff-jobs__header">
        <h1>Jobs</h1>
        <span className="ff-jobs__count">{total} total</span>
      </div>

      <div className="ff-jobs__status-filters">
        {counts.map(({ status, count }) => {
          const isBlocked = status === 'blocked'
          const highlight =
            isBlocked && count > 0 && query.status !== 'blocked'
          return (
            <button
              key={status}
              type="button"
              className={`ff-jobs__status-pill${
                query.status === status ? ' ff-jobs__status-pill--active' : ''
              }`}
              onClick={() => setStatus(status)}
            >
              {status === 'all' ? 'All' : status.replace(/_/g, ' ')}
              <span
                className={`ff-jobs__status-count${
                  highlight ? ' ff-jobs__status-count--highlight' : ''
                }`}
              >
                {count}
              </span>
            </button>
          )
        })}
      </div>

      <div className="ff-jobs__filters">
        <select
          className="ff-jobs__select"
          value={query.role}
          onChange={(e) => setRole(e.target.value)}
        >
          <option value="all">All Roles</option>
          {distinctRoles.map((role) => (
            <option key={role} value={role}>
              {role}
            </option>
          ))}
        </select>

        <input
          type="search"
          className="ff-jobs__search"
          placeholder="Search by summary…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
      </div>

      <div className="ff-jobs__table-wrap">
        <table className="ff-jobs__table">
          <thead>
            <tr>
              <th
                className="ff-jobs__th ff-jobs__th--sortable"
                onClick={() => toggleSort('id')}
              >
                ID {query.sort === 'id' && (query.dir === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="ff-jobs__th ff-jobs__th--sortable"
                onClick={() => toggleSort('summary')}
              >
                Summary{' '}
                {query.sort === 'summary' &&
                  (query.dir === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="ff-jobs__th ff-jobs__th--sortable"
                onClick={() => toggleSort('status')}
              >
                Status{' '}
                {query.sort === 'status' && (query.dir === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="ff-jobs__th ff-jobs__th--sortable"
                onClick={() => toggleSort('priority')}
              >
                Priority{' '}
                {query.sort === 'priority' &&
                  (query.dir === 'asc' ? '▲' : '▼')}
              </th>
              <th className="ff-jobs__th">Parent</th>
              <th className="ff-jobs__th">Role</th>
              <th className="ff-jobs__th">Assignee</th>
              <th
                className="ff-jobs__th ff-jobs__th--sortable"
                onClick={() => toggleSort('created_at')}
              >
                Created{' '}
                {query.sort === 'created_at' &&
                  (query.dir === 'asc' ? '▲' : '▼')}
              </th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr
                key={job.id}
                className="ff-jobs__row"
                onClick={() => navigate(`/jobs/${job.id}`)}
              >
                <td className="ff-jobs__td ff-jobs__td--id">#{job.id}</td>
                <td className="ff-jobs__td ff-jobs__td--summary">
                  {job.summary}
                </td>
                <td className="ff-jobs__td">
                  <StatusBadge status={job.status} />
                </td>
                <td className="ff-jobs__td ff-jobs__td--priority">
                  {job.priority}
                </td>
                <td className="ff-jobs__td ff-jobs__td--parent">
                  {job.parent_job_id ? (
                    <span data-tooltip={job.parent_job_summary ?? ''}>
                      #{job.parent_job_id}
                    </span>
                  ) : (
                    '-'
                  )}
                </td>
                <td className="ff-jobs__td">{job.target_role_label}</td>
                <td className="ff-jobs__td ff-jobs__td--mono">
                  {formatAssignee(job.assignee_agent_label)}
                </td>
                <td className="ff-jobs__td ff-jobs__td--date">
                  {formatDate(job.created_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {jobs.length === 0 && (
          <div className="ff-jobs__empty">No jobs match your filters.</div>
        )}
      </div>

      <div className="ff-jobs__footer">
        <Paginator
          total={total}
          limit={query.limit}
          offset={query.offset}
          onOffsetChange={setOffset}
          onLimitChange={setLimit}
        />
      </div>
    </div>
  )
}
