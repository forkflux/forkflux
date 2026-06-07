from src.exceptions import BaseValidationError


class ParentJobValidationError(BaseValidationError):
    code = "parent_job.invalid"
    msg = "Parent job is invalid."


class TargetRoleValidationError(BaseValidationError):
    code = "target_role.invalid"
    msg = "Target role is invalid."
