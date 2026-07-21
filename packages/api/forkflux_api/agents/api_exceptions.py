from forkflux_api.exceptions import BaseValidationError


class TargetRoleConflictValidationError(BaseValidationError):
    code = "target_role.conflict"
    msg = "Target role already exists."


class TargetRoleNotFoundValidationError(BaseValidationError):
    code = "target_role.not_found"
    msg = "One or more target roles were not found."
