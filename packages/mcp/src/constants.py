from enum import Enum, IntEnum


class JobStatusEnum(str, Enum):
    PUBLISHED = "published"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriorityEnum(IntEnum):
    LOW = 10
    NORMAL = 20
    HIGH = 30
    URGENT = 40
