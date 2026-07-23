"""Unit tests for ``resolve_event_type``.

Covers every valid transition defined in ``HandoffJobService.change_job_status``
plus the two override cases.
"""

import pytest
from forkflux_api.jobs.constants import (
    JobEventTypeEnum,
    JobStatusEnum,
    resolve_event_type,
)

# (previous, target, expected_event_type)
_TRANSITION_CASES = [
    # --- overrides (previous status matters) ---
    (JobStatusEnum.FAILED, JobStatusEnum.IN_PROGRESS, JobEventTypeEnum.TASK_RESTARTED),
    (JobStatusEnum.BLOCKED, JobStatusEnum.IN_PROGRESS, JobEventTypeEnum.TASK_UNBLOCKED),
    # --- defaults (target status drives the event type) ---
    (JobStatusEnum.CLAIMED, JobStatusEnum.IN_PROGRESS, JobEventTypeEnum.TASK_STARTED),
    (JobStatusEnum.UNBLOCKED, JobStatusEnum.IN_PROGRESS, JobEventTypeEnum.TASK_STARTED),
    (JobStatusEnum.IN_PROGRESS, JobStatusEnum.COMPLETED, JobEventTypeEnum.TASK_COMPLETED),
    (JobStatusEnum.IN_PROGRESS, JobStatusEnum.FAILED, JobEventTypeEnum.TASK_FAILED),
    (JobStatusEnum.CLAIMED, JobStatusEnum.FAILED, JobEventTypeEnum.TASK_FAILED),
    (JobStatusEnum.BLOCKED, JobStatusEnum.FAILED, JobEventTypeEnum.TASK_FAILED),
    (JobStatusEnum.UNBLOCKED, JobStatusEnum.FAILED, JobEventTypeEnum.TASK_FAILED),
    (JobStatusEnum.IN_PROGRESS, JobStatusEnum.BLOCKED, JobEventTypeEnum.TASK_BLOCKED),
    (JobStatusEnum.BLOCKED, JobStatusEnum.UNBLOCKED, JobEventTypeEnum.TASK_UNBLOCKED),
    (JobStatusEnum.PUBLISHED, JobStatusEnum.CANCELLED, JobEventTypeEnum.TASK_CANCELLED),
    (JobStatusEnum.CLAIMED, JobStatusEnum.CANCELLED, JobEventTypeEnum.TASK_CANCELLED),
    (JobStatusEnum.BLOCKED, JobStatusEnum.CANCELLED, JobEventTypeEnum.TASK_CANCELLED),
    (JobStatusEnum.UNBLOCKED, JobStatusEnum.CANCELLED, JobEventTypeEnum.TASK_CANCELLED),
]


@pytest.mark.parametrize(
    ("previous", "target", "expected"),
    _TRANSITION_CASES,
    ids=[f"{p.value}->{t.value}" for p, t, _ in _TRANSITION_CASES],
)
def test_resolve_event_type_returns_expected_event_type(
    previous: JobStatusEnum,
    target: JobStatusEnum,
    expected: JobEventTypeEnum,
) -> None:
    assert resolve_event_type(previous, target) is expected
