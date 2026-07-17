from enum import Enum, IntEnum


class JobStatusEnum(str, Enum):
    PUBLISHED = "published"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
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
