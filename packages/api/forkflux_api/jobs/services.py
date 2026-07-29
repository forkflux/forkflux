from datetime import datetime, timezone
from math import ceil, floor
from statistics import median
from typing import Any

import structlog

from forkflux_api.jobs.constants import (
    DependencyTypeEnum,
    JobEventTypeEnum,
    JobPriorityEnum,
    JobStatusEnum,
    resolve_event_type,
)
from forkflux_api.jobs.dto import (
    HandoffJobCreate,
    HandoffJobFilterParams,
    HandoffJobItem,
    HandoffJobRawStats,
    HandoffJobStats,
    HandoffJobUiPage,
    HandoffJobUpdate,
    HandoffJobWithArtifacts,
    HandoffJobWithArtifactsAndEvents,
    JobArtifactCreate,
    JobDependencyCreate,
    JobEventCreate,
    ReopenContext,
    RoutingRuleCreate,
)
from forkflux_api.jobs.exceptions import HandoffJobConflictError, HandoffJobNotFoundError
from forkflux_api.jobs.mcp_schemas import HandoffJobCreateRequest
from forkflux_api.jobs.models import HandoffJob
from forkflux_api.jobs.repositories import (
    HandoffJobRepository,
    JobArtifactRepository,
    JobDependencyRepository,
    JobEventRepository,
)


class HandoffJobService:
    MINUTES_SAVED_PER_HANDOFF = 8  # this number is taken from team measurement

    def __init__(
        self,
        handoff_job_repo: HandoffJobRepository,
        job_artifact_repo: JobArtifactRepository,
        job_event_repo: JobEventRepository,
        job_dependency_repo: JobDependencyRepository,
        trace_id: str,
    ) -> None:
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)
        self._handoff_job_repo = handoff_job_repo
        self._job_artifact_repo = job_artifact_repo
        self._job_event_repo = job_event_repo
        self._job_dependency_repo = job_dependency_repo

    @staticmethod
    def _duration_minutes(started_at: datetime, finished_at: datetime) -> float:
        return (finished_at - started_at).total_seconds() / 60

    @staticmethod
    def _median_or_none(values: list[float]) -> float | None:
        if not values:
            return None

        return float(median(values))

    @staticmethod
    def _percentile_or_none(values: list[float], percentile: float) -> float | None:
        if not values:
            return None

        sorted_values = sorted(values)
        position = (len(sorted_values) - 1) * percentile
        lower_idx = floor(position)
        upper_idx = ceil(position)

        if lower_idx == upper_idx:
            return float(sorted_values[lower_idx])

        lower = sorted_values[lower_idx]
        upper = sorted_values[upper_idx]
        weight = position - lower_idx
        return float(lower + ((upper - lower) * weight))

    async def stats(self, window_hours: int = 24, stuck_minutes: int = 60) -> HandoffJobStats:
        log = self._logger.bind(method="stats", window_hours=window_hours, stuck_minutes=stuck_minutes)
        log.info("operation_started")

        raw_stats: HandoffJobRawStats = await self._handoff_job_repo.stats(
            window_hours=window_hours,
            stuck_minutes=stuck_minutes,
        )
        status_counts = {status: raw_stats.status_counts.get(status, 0) for status in JobStatusEnum}
        all_time_status_counts = {status: raw_stats.all_time_status_counts.get(status, 0) for status in JobStatusEnum}
        queue_status_counts = {
            JobStatusEnum.PUBLISHED: status_counts[JobStatusEnum.PUBLISHED],
            JobStatusEnum.IN_PROGRESS: status_counts[JobStatusEnum.IN_PROGRESS],
            JobStatusEnum.BLOCKED: status_counts[JobStatusEnum.BLOCKED],
            JobStatusEnum.UNBLOCKED: status_counts[JobStatusEnum.UNBLOCKED],
        }
        terminal_status_counts = {
            JobStatusEnum.COMPLETED: status_counts[JobStatusEnum.COMPLETED],
            JobStatusEnum.FAILED: status_counts[JobStatusEnum.FAILED],
            JobStatusEnum.CANCELLED: status_counts[JobStatusEnum.CANCELLED],
        }

        completed_jobs = status_counts[JobStatusEnum.COMPLETED]
        failed_jobs = status_counts[JobStatusEnum.FAILED]
        blocked_jobs = status_counts[JobStatusEnum.BLOCKED]
        total_handoffs = raw_stats.total_handoffs
        estimated_time_saved_minutes = total_handoffs * self.MINUTES_SAVED_PER_HANDOFF
        completion_rate = (completed_jobs / raw_stats.total_jobs) if raw_stats.total_jobs > 0 else 0.0
        failure_rate = (failed_jobs / raw_stats.total_jobs) if raw_stats.total_jobs > 0 else 0.0
        blocked_rate = (blocked_jobs / raw_stats.total_jobs) if raw_stats.total_jobs > 0 else 0.0

        time_to_resolution_minutes = [
            self._duration_minutes(published_at, resolved_at)
            for published_at, resolved_at in raw_stats.published_to_resolution_pairs
            if published_at is not None and resolved_at is not None and resolved_at >= published_at
        ]

        log.info(
            "operation_completed",
            total_jobs=raw_stats.total_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            blocked_jobs=blocked_jobs,
            active_agents=raw_stats.active_agents,
            stuck_jobs=raw_stats.stuck_jobs,
            total_handoffs=total_handoffs,
            estimated_time_saved_minutes=estimated_time_saved_minutes,
            time_to_resolution_samples=len(time_to_resolution_minutes),
        )

        return HandoffJobStats(
            window_hours=raw_stats.window_hours,
            stuck_minutes=raw_stats.stuck_minutes,
            total_jobs=raw_stats.total_jobs,
            all_time_status_counts=all_time_status_counts,
            queue_status_counts=queue_status_counts,
            terminal_status_counts=terminal_status_counts,
            completion_rate=completion_rate,
            failure_rate=failure_rate,
            blocked_rate=blocked_rate,
            active_agents=raw_stats.active_agents,
            stuck_jobs=raw_stats.stuck_jobs,
            total_handoffs=total_handoffs,
            estimated_time_saved_minutes=estimated_time_saved_minutes,
            waiting_jobs_by_role=raw_stats.waiting_jobs_by_role,
            p50_time_to_resolution_minutes=self._median_or_none(time_to_resolution_minutes),
            p90_time_to_resolution_minutes=self._percentile_or_none(time_to_resolution_minutes, 0.9),
        )

    async def create_job(
        self,
        job_data: HandoffJobCreateRequest,
        target_role_id: int,
        source_agent_id: int,
        routing_rules: list[RoutingRuleCreate] | None = None,
    ) -> int:
        log = self._logger.bind(method="create_job")
        log.info("operation_started")

        # Deduplicate blocked_by IDs to prevent unique constraint failures on dependency edges.
        blocked_by = list(dict.fromkeys(job_data.blocked_by or []))

        # Determine initial status: PENDING if there are unmet blockers, PUBLISHED otherwise.
        status = JobStatusEnum.PENDING if blocked_by else JobStatusEnum.PUBLISHED

        job = HandoffJobCreate(
            parent_job_id=job_data.parent_job_id,
            summary=job_data.summary,
            context_payload=job_data.context_payload,
            priority=job_data.priority,
            source_agent_id=source_agent_id,
            target_role_id=target_role_id,
            constraints=job_data.constraints,
            blocked_by=blocked_by,
            routing_rules=routing_rules,
        )

        created_job = await self._handoff_job_repo.create(dto=job, status=status)
        log = log.bind(job_id=created_job.id)

        # Create BLOCKS dependency edges for each upstream job.
        if blocked_by:
            dependency_dtos = [
                JobDependencyCreate(
                    upstream_job_id=upstream_id,
                    downstream_job_id=created_job.id,
                    dep_type=DependencyTypeEnum.BLOCKS,
                )
                for upstream_id in blocked_by
            ]
            await self._job_dependency_repo.bulk_create(dtos=dependency_dtos)

            # Check if any upstream blocker is already terminally failed.
            # If so, propagate the matching terminal status (FAILED → FAILED,
            # CANCELLED → CANCELLED) to the new job instead of leaving it PENDING.
            failed_blockers = await self._job_dependency_repo.find_failed_blockers(downstream_job_id=created_job.id)
            if failed_blockers:
                # Use the first failed blocker's status as the propagation target.
                # When multiple blockers are terminally failed, the first one wins
                # (deterministic by query order); provenance records all failed IDs.
                propagated_status = failed_blockers[0][1]
                failed_ids = [fb[0] for fb in failed_blockers]
                timestamp = datetime.now(timezone.utc)
                created_job.status = propagated_status
                if propagated_status == JobStatusEnum.FAILED:
                    created_job.failure_reason = (
                        f"Upstream blocker(s) {failed_ids} reached terminal failure at creation time"
                    )
                    created_job.failed_at = timestamp
                else:  # CANCELLED
                    created_job.cancelled_at = timestamp
                created_job.updated_at = timestamp
                await self._handoff_job_repo.save(job=created_job)
                status = propagated_status
                log.info(
                    "barrier_sync_immediate_failure",
                    failed_blocker_ids=failed_ids,
                    propagated_status=propagated_status.value,
                )
            else:
                # If all upstream blockers are already COMPLETED, transition to PUBLISHED immediately.
                unmet = await self._job_dependency_repo.count_unmet_blockers(downstream_job_id=created_job.id)
                if unmet == 0:
                    created_job.status = JobStatusEnum.PUBLISHED
                    created_job.published_at = datetime.now(timezone.utc)
                    await self._handoff_job_repo.save(job=created_job)
                    status = JobStatusEnum.PUBLISHED
                    log.info("barrier_sync_immediate_activation", unmet_blockers=0)

        artifact_dtos = [
            JobArtifactCreate(
                job_id=created_job.id,
                artifact_type=artifact.type,
                artifact_uri=artifact.uri,
                artifact_checksum=artifact.checksum,
                metadata_json=artifact.metadata_json,
            )
            for artifact in job_data.artifacts
        ]
        await self._job_artifact_repo.bulk_create(dtos=artifact_dtos)

        event_type = (
            resolve_event_type(JobStatusEnum.PENDING, status) if blocked_by else JobEventTypeEnum.TASK_PUBLISHED
        )
        await self._job_event_repo.create(
            dto=JobEventCreate(
                job_id=created_job.id,
                event_type=event_type,
                current_status=status,
                actor_agent_id=source_agent_id,
                payload_json={
                    "priority": job_data.priority.value,
                    "target_role_id": target_role_id,
                    "artifact_count": len(artifact_dtos),
                    "blocked_by": blocked_by,
                },
            )
        )

        log.info("operation_completed", artifact_count=len(artifact_dtos), status=status.value)
        return created_job.id

    async def get_job(self, job_id: int) -> HandoffJobItem:
        log = self._logger.bind(method="get_job", job_id=job_id)
        log.info("operation_started")

        job = await self._handoff_job_repo.get(job_id)

        log.info("operation_completed")
        return job

    async def count_existing_job_ids(self, job_ids: list[int]) -> int:
        """Count how many of the given job IDs exist (single batch query)."""
        log = self._logger.bind(method="count_existing_job_ids", job_id_count=len(job_ids))
        log.info("operation_started")

        count = await self._handoff_job_repo.count_existing_job_ids(job_ids)

        log.info("operation_completed", existing_count=count)
        return count

    async def get_job_with_artifacts(self, job_id: int) -> HandoffJobWithArtifacts:
        log = self._logger.bind(method="get_job_with_artifacts", job_id=job_id)
        log.info("operation_started")

        job = await self._handoff_job_repo.get(job_id)
        artifacts = await self._job_artifact_repo.list(job_id=job_id)

        log.info("operation_completed", artifact_count=len(artifacts))
        return {"job": job, "artifacts": artifacts}

    async def get_ui_job_with_artifacts_and_events(self, job_id: int) -> HandoffJobWithArtifactsAndEvents:
        log = self._logger.bind(method="get_ui_job_with_artifacts_and_events", job_id=job_id)
        log.info("operation_started")

        job = await self._handoff_job_repo.ui_get(job_id)
        artifacts = await self._job_artifact_repo.list(job_id=job_id)
        events = await self._job_event_repo.ui_list(job_id=job_id)
        upstream_dependencies, downstream_dependencies = await self._job_dependency_repo.ui_list_for_job(job_id)

        log.info(
            "operation_completed",
            artifact_count=len(artifacts),
            event_count=len(events),
            upstream_dependency_count=len(upstream_dependencies),
            downstream_dependency_count=len(downstream_dependencies),
        )
        return {
            "job": job,
            "artifacts": artifacts,
            "events": events,
            "upstream_dependencies": upstream_dependencies,
            "downstream_dependencies": downstream_dependencies,
        }

    async def list_jobs(self, filter_params: HandoffJobFilterParams) -> list[HandoffJobItem]:
        log = self._logger.bind(
            method="list_jobs",
            statuses=[status.value for status in filter_params.statuses],
            target_role_ids=filter_params.target_role_ids,
            limit=filter_params.limit,
            order=[order.value for order in filter_params.order],
        )
        log.info("operation_started")

        jobs = await self._handoff_job_repo.list(filter_params=filter_params)

        log.info("operation_completed", jobs_count=len(jobs))
        return jobs

    async def list_ui_jobs(self, filter_params: HandoffJobFilterParams) -> HandoffJobUiPage:
        log = self._logger.bind(
            method="list_ui_jobs",
            statuses=[status.value for status in filter_params.statuses],
            target_role_ids=filter_params.target_role_ids,
            limit=filter_params.limit,
            offset=filter_params.offset,
            order=[order.value for order in filter_params.order],
        )
        log.info("operation_started")

        items = await self._handoff_job_repo.ui_list(filter_params=filter_params)
        total = await self._handoff_job_repo.ui_count(filter_params=filter_params)

        log.info("operation_completed", items_count=len(items), total=total)
        return HandoffJobUiPage(
            items=items,
            total=total,
            limit=filter_params.limit,
            offset=filter_params.offset,
        )

    async def count_jobs_by_status(self) -> dict[JobStatusEnum, int]:
        log = self._logger.bind(method="count_jobs_by_status")
        log.info("operation_started")

        status_counts = await self._handoff_job_repo.count_by_status()

        log.info("operation_completed", status_counts=status_counts)
        return status_counts

    async def delete_job(self, job_id: int) -> None:
        log = self._logger.bind(method="delete_job", job_id=job_id)
        log.info("operation_started")

        await self._handoff_job_repo.delete(job_id=job_id)

        log.info("operation_completed")

    async def claim_job(self, job_id: int, agent_id: int, agent_role_ids: list[int]) -> None:
        log = self._logger.bind(method="claim_job", job_id=job_id, agent_id=agent_id, agent_role_ids=agent_role_ids)
        log.info("operation_started")

        job = await self._handoff_job_repo.get_by_id_for_update(job_id=job_id)

        if job.status != JobStatusEnum.PUBLISHED:
            log.warning(
                "operation_failed",
                reason="invalid_status",
                current_status=job.status.value,
            )
            raise HandoffJobConflictError

        if job.target_role_id not in agent_role_ids:
            log.warning(
                "operation_failed",
                reason="role_mismatch",
                target_role_id=job.target_role_id,
            )
            raise HandoffJobConflictError

        if job.assignee_agent_id is not None:
            log.warning(
                "operation_failed",
                reason="already_assigned",
                assignee_agent_id=job.assignee_agent_id,
            )
            raise HandoffJobConflictError

        timestamp = datetime.now(timezone.utc)

        job.status = JobStatusEnum.IN_PROGRESS
        job.assignee_agent_id = agent_id
        job.started_at = timestamp

        await self._handoff_job_repo.save(job=job)
        log.info("operation_completed")

    async def change_job_status(
        self,
        job_id: int,
        status: JobStatusEnum,
        agent_id: int | None = None,
        failure_reason: str | None = None,
        blocked_reason: str | None = None,
        unblock_reason: str | None = None,
    ) -> tuple[JobStatusEnum, JobStatusEnum]:
        log = self._logger.bind(
            method="change_job_status", job_id=job_id, target_status=status.value, agent_id=agent_id
        )
        log.info("operation_started")

        job = await self._handoff_job_repo.get_by_id_for_update(job_id=job_id)
        current_status = job.status

        allowed_transitions = {
            (JobStatusEnum.PENDING, JobStatusEnum.CANCELLED),
            (JobStatusEnum.IN_PROGRESS, JobStatusEnum.COMPLETED),
            (JobStatusEnum.IN_PROGRESS, JobStatusEnum.FAILED),
            (JobStatusEnum.IN_PROGRESS, JobStatusEnum.BLOCKED),
            (JobStatusEnum.FAILED, JobStatusEnum.IN_PROGRESS),
            (JobStatusEnum.BLOCKED, JobStatusEnum.UNBLOCKED),
            (JobStatusEnum.BLOCKED, JobStatusEnum.FAILED),
            (JobStatusEnum.BLOCKED, JobStatusEnum.CANCELLED),
            (JobStatusEnum.UNBLOCKED, JobStatusEnum.IN_PROGRESS),
            (JobStatusEnum.UNBLOCKED, JobStatusEnum.FAILED),
            (JobStatusEnum.UNBLOCKED, JobStatusEnum.CANCELLED),
            (JobStatusEnum.PUBLISHED, JobStatusEnum.CANCELLED),
        }

        if (current_status, status) not in allowed_transitions:
            log.warning(
                "operation_failed",
                reason="invalid_status_transition",
                current_status=current_status.value,
            )
            raise HandoffJobConflictError

        if status == JobStatusEnum.UNBLOCKED and agent_id is None:
            pass  # UI/admin unblock — skip assignee authorization check
        elif current_status in (JobStatusEnum.PENDING, JobStatusEnum.PUBLISHED) and status == JobStatusEnum.CANCELLED:
            if job.source_agent_id != agent_id:
                log.warning(
                    "operation_failed",
                    reason="source_agent_mismatch",
                    source_agent_id=job.source_agent_id,
                )
                raise HandoffJobConflictError
        elif job.assignee_agent_id != agent_id:
            log.warning(
                "operation_failed",
                reason="assignee_mismatch",
                assignee_agent_id=job.assignee_agent_id,
            )
            raise HandoffJobConflictError

        # Enforce max_retries on the FAILED → IN_PROGRESS restart path.
        # This prevents infinite retry loops via manual restarts, mirroring
        # the guard already present in reject_job. Runs after the assignee/source
        # authorization chain so only authorized retry restarts increment and log.
        if current_status == JobStatusEnum.FAILED and status == JobStatusEnum.IN_PROGRESS:
            if job.retry_count >= job.max_retries:
                log.warning(
                    "operation_failed",
                    reason="max_retries_exceeded",
                    retry_count=job.retry_count,
                    max_retries=job.max_retries,
                )
                raise HandoffJobConflictError

            job.retry_count += 1
            log.info("retry_restart", retry_count=job.retry_count, max_retries=job.max_retries)

        timestamp = datetime.now(timezone.utc)
        job.status = status
        job.updated_at = timestamp

        event_type = resolve_event_type(current_status, status)
        event_payload: dict[str, Any] = {"timestamp": timestamp.isoformat()}

        # Clear fields from the previous problem state (if any).
        job.cancelled_at = None
        job.failed_at = None
        job.failure_reason = None
        job.blocked_at = None
        job.blocked_reason = None
        job.unblock_reason = None
        job.unblocked_at = None

        # Set fields for the target state.
        if status == JobStatusEnum.IN_PROGRESS:
            job.started_at = timestamp
            if current_status == JobStatusEnum.FAILED:
                event_payload["retry_count"] = job.retry_count
        elif status == JobStatusEnum.COMPLETED:
            job.completed_at = timestamp
        elif status == JobStatusEnum.FAILED:
            job.failure_reason = failure_reason
            job.failed_at = timestamp
            event_payload["failure_reason"] = failure_reason
        elif status == JobStatusEnum.BLOCKED:
            job.blocked_reason = blocked_reason
            job.blocked_at = timestamp
            event_payload["blocked_reason"] = blocked_reason
        elif status == JobStatusEnum.UNBLOCKED:
            if not unblock_reason:
                log.warning(
                    "operation_failed",
                    reason="missing_unblock_reason",
                    current_status=current_status.value,
                )
                raise HandoffJobConflictError
            job.unblock_reason = unblock_reason
            job.unblocked_at = timestamp
            event_payload["unblock_reason"] = unblock_reason
        elif status == JobStatusEnum.CANCELLED:
            job.cancelled_at = timestamp

        await self._handoff_job_repo.save(job=job)

        # Conditional routing: evaluate routing rules and auto-create downstream jobs.
        # This happens BEFORE the completion event is created, so the event payload
        # can include routed_job_ids provenance.
        if status == JobStatusEnum.COMPLETED:
            routed_job_ids = await self._evaluate_routing_rules(completed_job=job, actor_agent_id=agent_id)
            if routed_job_ids:
                event_payload["routed_job_ids"] = routed_job_ids

        await self._job_event_repo.create(
            dto=JobEventCreate(
                job_id=job_id,
                event_type=event_type,
                current_status=status,
                actor_agent_id=agent_id,
                payload_json=event_payload,
            )
        )

        # Barrier sync happens AFTER the completion event is recorded, so the
        # completion event is logged first, followed by downstream activation events.
        if status == JobStatusEnum.COMPLETED:
            await self._barrier_sync(upstream_job_id=job_id, actor_agent_id=agent_id)
        elif status in (JobStatusEnum.FAILED, JobStatusEnum.CANCELLED):
            await self._propagate_terminal_failure(
                upstream_job_id=job_id, terminal_status=status, actor_agent_id=agent_id
            )

        log.info("operation_completed", previous_status=current_status.value, current_status=status.value)
        return current_status, status

    async def _barrier_sync(self, upstream_job_id: int, actor_agent_id: int | None) -> None:
        """Check downstream PENDING jobs and activate those whose blockers are all COMPLETED."""
        log = self._logger.bind(method="_barrier_sync", upstream_job_id=upstream_job_id)
        log.info("operation_started")

        downstream_ids = await self._job_dependency_repo.find_downstream_pending_job_ids(
            upstream_job_id=upstream_job_id
        )

        if not downstream_ids:
            log.info("operation_completed", activated_count=0)
            return

        activated_count = 0
        timestamp = datetime.now(timezone.utc)

        for downstream_id in downstream_ids:
            unmet = await self._job_dependency_repo.count_unmet_blockers(downstream_job_id=downstream_id)
            if unmet > 0:
                continue

            downstream_job = await self._handoff_job_repo.get_by_id_for_update(job_id=downstream_id)
            if downstream_job.status != JobStatusEnum.PENDING:
                continue

            downstream_job.status = JobStatusEnum.PUBLISHED
            downstream_job.published_at = timestamp
            downstream_job.updated_at = timestamp
            await self._handoff_job_repo.save(job=downstream_job)

            await self._job_event_repo.create(
                dto=JobEventCreate(
                    job_id=downstream_id,
                    event_type=JobEventTypeEnum.TASK_ACTIVATED,
                    current_status=JobStatusEnum.PUBLISHED,
                    actor_agent_id=actor_agent_id,
                    payload_json={
                        "timestamp": timestamp.isoformat(),
                        "activated_by": upstream_job_id,
                        "reason": "barrier_sync_all_blockers_completed",
                    },
                )
            )
            activated_count += 1
            log.info("barrier_sync_activated_job", downstream_job_id=downstream_id)

        log.info("operation_completed", activated_count=activated_count)

    async def _propagate_terminal_failure(
        self, upstream_job_id: int, terminal_status: JobStatusEnum, actor_agent_id: int | None
    ) -> None:
        """Propagate terminal failure to downstream PENDING jobs when an upstream blocker fails.

        Mirrors ``_barrier_sync`` but handles the case where an upstream blocker
        reaches FAILED or CANCELLED. Downstream PENDING jobs that have any
        terminally-failed blocker are transitioned to the matching terminal status
        (FAILED → FAILED, CANCELLED → CANCELLED) with explicit provenance, so they
        do not remain stuck in PENDING indefinitely.
        """
        log = self._logger.bind(
            method="_propagate_terminal_failure",
            upstream_job_id=upstream_job_id,
            terminal_status=terminal_status.value,
        )
        log.info("operation_started")

        downstream_ids = await self._job_dependency_repo.find_downstream_pending_job_ids(
            upstream_job_id=upstream_job_id
        )

        if not downstream_ids:
            log.info("operation_completed", propagated_count=0)
            return

        propagated_count = 0
        timestamp = datetime.now(timezone.utc)

        for downstream_id in downstream_ids:
            failed_blockers = await self._job_dependency_repo.find_failed_blockers(downstream_job_id=downstream_id)
            if not failed_blockers:
                continue

            downstream_job = await self._handoff_job_repo.get_by_id_for_update(job_id=downstream_id)
            if downstream_job.status != JobStatusEnum.PENDING:
                continue

            # Use the triggering upstream's terminal status as the propagation target.
            propagated_status = terminal_status
            failed_ids = [fb[0] for fb in failed_blockers]

            downstream_job.status = propagated_status
            downstream_job.updated_at = timestamp
            if propagated_status == JobStatusEnum.FAILED:
                downstream_job.failure_reason = f"Upstream blocker(s) {failed_ids} reached terminal failure"
                downstream_job.failed_at = timestamp
            else:  # CANCELLED
                downstream_job.cancelled_at = timestamp
            await self._handoff_job_repo.save(job=downstream_job)

            await self._job_event_repo.create(
                dto=JobEventCreate(
                    job_id=downstream_id,
                    event_type=JobEventTypeEnum.TASK_FAILED
                    if propagated_status == JobStatusEnum.FAILED
                    else JobEventTypeEnum.TASK_CANCELLED,
                    current_status=propagated_status,
                    actor_agent_id=actor_agent_id,
                    payload_json={
                        "timestamp": timestamp.isoformat(),
                        "failed_by": upstream_job_id,
                        "upstream_terminal_status": terminal_status.value,
                        "failed_blocker_ids": failed_ids,
                        "reason": "barrier_sync_upstream_terminal_failure",
                    },
                )
            )
            propagated_count += 1
            log.info("barrier_sync_failed_job", downstream_job_id=downstream_id)

        log.info("operation_completed", propagated_count=propagated_count)

    async def _evaluate_routing_rules(self, completed_job: HandoffJob, actor_agent_id: int | None) -> list[int]:
        """Evaluate routing rules on a completed job and auto-create downstream jobs.

        This is the conditional routing feature (Phase 3). When a job with
        ``routing_rules`` transitions to ``COMPLETED``, each rule is used to
        create a new ``PUBLISHED`` job. The new job's ``parent_job_id`` is set
        to the completing job's ID, and its ``context_payload`` is enhanced
        with ``routed_from_job_id``.

        This is **opt-in**: jobs without routing rules (``None`` or empty list)
        return an empty list and behave exactly as before.

        If a routing rule's ``target_role_id`` no longer exists (role was
        deleted between creation and completion), the FK constraint will fail.
        The service catches this, logs a warning, and skips that rule — the
        job still completes successfully.

        Returns a list of created job IDs (empty if no rules fired).
        """
        rules = completed_job.routing_rules
        if not rules:
            return []

        log = self._logger.bind(
            method="_evaluate_routing_rules",
            completed_job_id=completed_job.id,
            rule_count=len(rules),
        )
        log.info("operation_started")

        created_job_ids: list[int] = []

        for rule in rules:
            target_role_id = rule.get("target_role_id")
            if target_role_id is None:
                log.warning("routing_rule_skipped", reason="missing_target_role_id")
                continue

            rule_summary = rule.get("summary", "")
            rule_context = rule.get("context_payload", {})
            rule_constraints = rule.get("constraints", [])
            rule_priority = JobPriorityEnum(rule.get("priority", JobPriorityEnum.NORMAL.value))
            rule_artifacts = rule.get("artifacts", [])

            # Enhance context with routing provenance.
            routed_context = {
                **rule_context,
                "routed_from_job_id": completed_job.id,
            }

            job_dto = HandoffJobCreate(
                parent_job_id=completed_job.id,
                summary=rule_summary,
                context_payload=routed_context,
                priority=rule_priority,
                source_agent_id=completed_job.source_agent_id,
                target_role_id=target_role_id,
                constraints=rule_constraints,
            )

            try:
                created_job = await self._handoff_job_repo.create_in_savepoint(
                    dto=job_dto, status=JobStatusEnum.PUBLISHED
                )
            except HandoffJobConflictError:
                log.warning(
                    "routing_rule_skipped",
                    reason="target_role_id_fk_violation",
                    target_role_id=target_role_id,
                )
                continue

            # Create artifacts for the routed job.
            if rule_artifacts:
                artifact_dtos = [
                    JobArtifactCreate(
                        job_id=created_job.id,
                        artifact_type=artifact.get("type", ""),
                        artifact_uri=artifact.get("uri", ""),
                        artifact_checksum=artifact.get("checksum"),
                        metadata_json=artifact.get("metadata_json", {}),
                    )
                    for artifact in rule_artifacts
                ]
                await self._job_artifact_repo.bulk_create(dtos=artifact_dtos)

            # Create a TASK_PUBLISHED event with routing provenance.
            await self._job_event_repo.create(
                dto=JobEventCreate(
                    job_id=created_job.id,
                    event_type=JobEventTypeEnum.TASK_PUBLISHED,
                    current_status=JobStatusEnum.PUBLISHED,
                    actor_agent_id=actor_agent_id,
                    payload_json={
                        "routed_from_job_id": completed_job.id,
                        "target_role_id": target_role_id,
                        "priority": rule_priority.value,
                    },
                )
            )

            created_job_ids.append(created_job.id)
            log.info(
                "routing_rule_created_job",
                routed_job_id=created_job.id,
                target_role_id=target_role_id,
            )

        # Create a TASK_ROUTED event on the completing job for audit trail.
        if created_job_ids:
            await self._job_event_repo.create(
                dto=JobEventCreate(
                    job_id=completed_job.id,
                    event_type=JobEventTypeEnum.TASK_ROUTED,
                    current_status=JobStatusEnum.COMPLETED,
                    actor_agent_id=actor_agent_id,
                    payload_json={
                        "routed_job_ids": created_job_ids,
                        "rule_count": len(rules),
                    },
                )
            )

        log.info("operation_completed", created_job_count=len(created_job_ids))
        return created_job_ids

    MAX_REJECTION_REASON_LENGTH = 2000

    async def reject_job(
        self,
        job_id: int,
        target_job_id: int,
        reason: str,
        source_agent_id: int,
    ) -> tuple[int, int]:
        """Create a reopen iteration of target_job_id with retry_count + 1.

        Authorization: the caller must be the assignee of job_id, which must be
        IN_PROGRESS. The target_job_id must be COMPLETED.

        The new job inherits the target role and constraints from the original job.
        A REOPEN_OF dependency edge links the new job to the original.
        The rejection reason is stored as a structured ``rejection_reason`` artifact
        (authoritative source of truth). It is also copied into ``context_payload``
        as legacy compatibility data for jobs that may be read by pre-Phase 2 consumers.
        """
        log = self._logger.bind(
            method="reject_job",
            job_id=job_id,
            target_job_id=target_job_id,
            source_agent_id=source_agent_id,
        )
        log.info("operation_started")

        # Authorization: fetch the reviewing job and verify the caller is its assignee.
        try:
            reviewing_job = await self._handoff_job_repo.get_by_id_for_update(job_id=job_id)
        except HandoffJobNotFoundError:
            log.warning("operation_failed", reason="reviewing_job_not_found", job_id=job_id)
            raise HandoffJobNotFoundError(which="job_id") from None

        if reviewing_job.assignee_agent_id != source_agent_id:
            log.warning(
                "operation_failed",
                reason="not_assignee_of_reviewing_job",
                assignee_agent_id=reviewing_job.assignee_agent_id,
            )
            raise HandoffJobConflictError

        if reviewing_job.status != JobStatusEnum.IN_PROGRESS:
            log.warning(
                "operation_failed",
                reason="reviewing_job_not_in_progress",
                current_status=reviewing_job.status.value,
            )
            raise HandoffJobConflictError

        # The target job must be COMPLETED.
        try:
            original_job = await self._handoff_job_repo.get_by_id_for_update(job_id=target_job_id)
        except HandoffJobNotFoundError:
            log.warning("operation_failed", reason="target_job_not_found", target_job_id=target_job_id)
            raise HandoffJobNotFoundError(which="target_job_id") from None

        if original_job.status != JobStatusEnum.COMPLETED:
            log.warning(
                "operation_failed",
                reason="target_job_not_completed",
                target_status=original_job.status.value,
            )
            raise HandoffJobConflictError

        # Verify the reviewing job (job_id) is blocked by the target job (target_job_id).
        # This ensures the reviewer can only reject work it was waiting on.
        has_edge = await self._job_dependency_repo.has_blocks_edge(
            upstream_job_id=target_job_id,
            downstream_job_id=job_id,
        )
        if not has_edge:
            log.warning(
                "operation_failed",
                reason="no_blocks_edge_from_target_to_reviewer",
                target_job_id=target_job_id,
                reviewing_job_id=job_id,
            )
            raise HandoffJobConflictError

        # Enforce max_retries: reject if the original job has already exhausted its retry budget.
        if original_job.retry_count >= original_job.max_retries:
            log.warning(
                "operation_failed",
                reason="max_retries_exceeded",
                retry_count=original_job.retry_count,
                max_retries=original_job.max_retries,
            )
            raise HandoffJobConflictError

        # Enforce reason length limit to prevent payload/log poisoning.
        truncated_reason = reason[: self.MAX_REJECTION_REASON_LENGTH]

        new_retry_count = original_job.retry_count + 1

        job = HandoffJobCreate(
            parent_job_id=original_job.parent_job_id,
            summary=f"[Retry {new_retry_count}] {original_job.summary}",
            context_payload={
                **original_job.context_payload,
                # NOTE: These context_payload fields are legacy compatibility
                # data only. The authoritative source of truth for the rejection
                # reason is the rejection_reason artifact created below.
                # get_reopen_context() reads the artifact first and falls back to
                # these fields only for jobs created before Phase 2.
                "rejection_reason": truncated_reason,
                "rejected_by_job_id": job_id,
                "original_job_id": target_job_id,
                "retry_count": new_retry_count,
            },
            priority=JobPriorityEnum(original_job.priority),
            source_agent_id=source_agent_id,
            target_role_id=original_job.target_role_id,
            constraints=original_job.constraints,
            retry_count=new_retry_count,
            max_retries=original_job.max_retries,
        )

        created_job = await self._handoff_job_repo.create(dto=job, status=JobStatusEnum.PUBLISHED)
        log = log.bind(new_job_id=created_job.id)

        # Store the rejection reason as a structured artifact on the new job.
        # This makes the reason queryable and durable as a first-class artifact,
        # not buried in the context_payload JSON blob.
        await self._job_artifact_repo.bulk_create(
            dtos=[
                JobArtifactCreate(
                    job_id=created_job.id,
                    artifact_type="rejection_reason",
                    artifact_uri="inline://rejection_reason",
                    artifact_checksum=None,
                    metadata_json={
                        "reason": truncated_reason,
                        "original_job_id": target_job_id,
                        "rejected_by_job_id": job_id,
                        "retry_count": new_retry_count,
                    },
                )
            ]
        )

        # Create REOPEN_OF edge from original to retry (version lineage).
        # Create new BLOCKS edge from retry to reviewer (so reviewer is reactivated when retry completes).
        await self._job_dependency_repo.bulk_create(
            dtos=[
                JobDependencyCreate(
                    upstream_job_id=target_job_id,
                    downstream_job_id=created_job.id,
                    dep_type=DependencyTypeEnum.REOPEN_OF,
                ),
                JobDependencyCreate(
                    upstream_job_id=created_job.id,
                    downstream_job_id=job_id,
                    dep_type=DependencyTypeEnum.BLOCKS,
                ),
            ]
        )

        # Delete the old BLOCKS edge from original to reviewer — the reviewer
        # is now blocked by the retry, not the original.
        await self._job_dependency_repo.delete_blocks_edge(
            upstream_job_id=target_job_id,
            downstream_job_id=job_id,
        )

        # Transition the reviewer from IN_PROGRESS to PENDING so it waits
        # for the retry to complete. Barrier sync will reactivate it.
        # Clear ownership fields so the reviewer can be claimed by any agent
        # when it returns to PUBLISHED.
        timestamp = datetime.now(timezone.utc)
        reviewing_job.status = JobStatusEnum.PENDING
        reviewing_job.assignee_agent_id = None
        reviewing_job.started_at = None
        reviewing_job.updated_at = timestamp
        await self._handoff_job_repo.save(job=reviewing_job)

        await self._job_event_repo.create(
            dto=JobEventCreate(
                job_id=created_job.id,
                event_type=JobEventTypeEnum.TASK_PUBLISHED,
                current_status=JobStatusEnum.PUBLISHED,
                actor_agent_id=source_agent_id,
                payload_json={
                    "retry_count": new_retry_count,
                    "max_retries": original_job.max_retries,
                    "rejected_by_job_id": job_id,
                    "original_job_id": target_job_id,
                    "rejection_reason": truncated_reason,
                },
            )
        )

        await self._job_event_repo.create(
            dto=JobEventCreate(
                job_id=job_id,
                event_type=JobEventTypeEnum.TASK_PENDING,
                current_status=JobStatusEnum.PENDING,
                actor_agent_id=source_agent_id,
                payload_json={
                    "timestamp": timestamp.isoformat(),
                    "reason": "rejected_upstream_retry_created",
                    "retry_job_id": created_job.id,
                },
            )
        )

        log.info(
            "operation_completed",
            retry_count=new_retry_count,
            reviewer_transitioned_to="pending",
        )
        return created_job.id, new_retry_count

    async def update_job(self, job_id: int, dto: HandoffJobUpdate, agent_id: int) -> None:
        log = self._logger.bind(method="update_job", job_id=job_id, agent_id=agent_id)
        log.info("operation_started")

        job = await self._handoff_job_repo.get_by_id_for_update(job_id=job_id)
        current_status = job.status

        changes: dict[str, dict[str, Any]] = {}
        if dto.context_payload is not None:
            changes["context_payload"] = {"old": job.context_payload, "new": dto.context_payload}
        if dto.constraints is not None:
            changes["constraints"] = {"old": job.constraints, "new": dto.constraints}

        await self._handoff_job_repo.update(job=job, dto=dto)

        timestamp = datetime.now(timezone.utc)
        await self._job_event_repo.create(
            dto=JobEventCreate(
                job_id=job_id,
                event_type=JobEventTypeEnum.TASK_UPDATED,
                current_status=current_status,
                actor_agent_id=agent_id,
                payload_json={
                    "timestamp": timestamp.isoformat(),
                    "changes": changes,
                },
            )
        )

        log.info("operation_completed", updated_fields=list(changes.keys()))

    REJECTION_REASON_ARTIFACT_TYPE = "rejection_reason"

    async def get_reopen_context(self, job_id: int) -> ReopenContext:
        """Return focused reopen context — only the diff/rejection metadata,
        not the full original ``context_payload``.

        This is the context-window-management feature: CLI agents with limited
        context windows get the rejection reason, retry count, and constraints
        without parsing the entire original context blob.

        The ``rejection_reason`` artifact is the authoritative source of truth.
        The ``context_payload`` fields (``rejection_reason``, ``original_job_id``,
        ``rejected_by_job_id``, ``retry_count``) are legacy compatibility data
        used as a fallback only for jobs created before Phase 2.

        Raises ``HandoffJobConflictError`` if the job is not a reopen iteration
        (i.e., its ``context_payload`` does not contain ``original_job_id``).
        """
        log = self._logger.bind(method="get_reopen_context", job_id=job_id)
        log.info("operation_started")

        job_item = await self._handoff_job_repo.get(job_id=job_id)
        job = job_item.job_details

        # A reopen iteration has ``original_job_id`` in its context_payload.
        original_job_id = job.context_payload.get("original_job_id")
        if original_job_id is None:
            log.warning(
                "operation_failed",
                reason="job_is_not_reopen_iteration",
                current_status=job.status.value,
            )
            raise HandoffJobConflictError

        rejected_by_job_id = job.context_payload.get("rejected_by_job_id", 0)

        # Prefer the structured rejection_reason artifact (Phase 2 source of truth).
        # Fall back to context_payload for jobs created before Phase 2.
        rejection_reason: str
        artifact = await self._job_artifact_repo.find_by_type(
            job_id=job_id,
            artifact_type=self.REJECTION_REASON_ARTIFACT_TYPE,
        )
        if artifact is not None:
            # Defensive: artifact metadata is JSON and may be externally modified.
            # Verify the reason value is a string before using it; otherwise fall
            # back to the legacy context_payload field.
            artifact_reason = artifact.metadata_json.get("reason")
            if isinstance(artifact_reason, str):
                rejection_reason = artifact_reason
            else:
                log.warning(
                    "artifact_reason_not_string",
                    reason_type=type(artifact_reason).__name__,
                )
                rejection_reason = job.context_payload.get("rejection_reason", "")
        else:
            rejection_reason = job.context_payload.get("rejection_reason", "")

        log.info("operation_completed", original_job_id=original_job_id, retry_count=job.retry_count)
        return ReopenContext(
            job_id=job.id,
            original_job_id=original_job_id,
            rejected_by_job_id=rejected_by_job_id,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
            rejection_reason=rejection_reason,
            summary=job.summary,
            constraints=job.constraints,
            target_role_key=job_item.target_role_key,
        )
