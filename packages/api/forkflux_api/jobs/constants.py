from enum import Enum, IntEnum


class JobStatusEnum(str, Enum):
    PUBLISHED = "published"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    UNBLOCKED = "unblocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriorityEnum(IntEnum):
    LOW = 10
    NORMAL = 20
    HIGH = 30
    URGENT = 40


class JobListOrderEnum(str, Enum):
    CREATED_AT_ASC = "created_at_asc"
    CREATED_AT_DESC = "created_at_desc"
    PRIORITY_ASC = "priority_asc"
    PRIORITY_DESC = "priority_desc"


class JobEventTypeEnum(str, Enum):
    TASK_PUBLISHED = "task_published"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_RESTARTED = "task_restarted"
    TASK_BLOCKED = "task_blocked"
    TASK_UNBLOCKED = "task_unblocked"
    TASK_UPDATED = "task_updated"


_DEFAULT_EVENT_TYPE_BY_TARGET: dict[JobStatusEnum, JobEventTypeEnum] = {
    JobStatusEnum.IN_PROGRESS: JobEventTypeEnum.TASK_STARTED,
    JobStatusEnum.COMPLETED: JobEventTypeEnum.TASK_COMPLETED,
    JobStatusEnum.FAILED: JobEventTypeEnum.TASK_FAILED,
    JobStatusEnum.BLOCKED: JobEventTypeEnum.TASK_BLOCKED,
    JobStatusEnum.UNBLOCKED: JobEventTypeEnum.TASK_UNBLOCKED,
    JobStatusEnum.CANCELLED: JobEventTypeEnum.TASK_CANCELLED,
}

_EVENT_TYPE_OVERRIDES: dict[tuple[JobStatusEnum, JobStatusEnum], JobEventTypeEnum] = {
    (JobStatusEnum.FAILED, JobStatusEnum.IN_PROGRESS): JobEventTypeEnum.TASK_RESTARTED,
}


def resolve_event_type(previous: JobStatusEnum, target: JobStatusEnum) -> JobEventTypeEnum:
    """Resolve the event type for a status transition.

    Most transitions map to a default event type based solely on the target
    status. One transition overrides this default because it represents
    recovery from a problem state rather than a fresh start:

    * ``FAILED -> IN_PROGRESS`` → ``TASK_RESTARTED``
    """
    return _EVENT_TYPE_OVERRIDES.get(
        (previous, target),
        _DEFAULT_EVENT_TYPE_BY_TARGET[target],
    )
