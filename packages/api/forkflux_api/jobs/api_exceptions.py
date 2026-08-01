from typing import Any, Literal

from forkflux_api.exceptions import BaseValidationError


class ParentJobValidationError(BaseValidationError):
    code = "parent_job.invalid"
    msg = "Parent job is invalid."


class BlockedByJobValidationError(BaseValidationError):
    code = "blocked_by_job.invalid"
    msg = "Blocked-by job is invalid."


class TargetRoleValidationError(BaseValidationError):
    code = "target_role.invalid"
    msg = "Target role is invalid."

    def __init__(
        self,
        field_name: str,
        value: Any = None,
        loc: Literal["body", "query", "header", "path"] = "body",
        available_roles: list[str] | None = None,
    ) -> None:
        role_keys = ", ".join(sorted(available_roles or [])) or "none"
        super().__init__(
            field_name=field_name,
            value=value,
            loc=loc,
            detail=f"Available roles: {role_keys}.",
        )


class HandoffJobClaimValidationError(BaseValidationError):
    code = "handoff_job_claim.invalid"
    msg = "Handoff job claim is invalid."


class HandoffJobIdentityValidationError(BaseValidationError):
    code = "handoff_job_identity.invalid"
    msg = "Handoff job identity is invalid."


class HandoffJobStatusValidationError(BaseValidationError):
    code = "handoff_job_status.invalid"
    msg = "Handoff job status transition is invalid."


class HandoffJobUpdateValidationError(BaseValidationError):
    code = "handoff_job_update.invalid"
    msg = "Handoff job update is invalid."


class RoutingRuleValidationError(BaseValidationError):
    code = "routing_rule.invalid"
    msg = "Routing rule is invalid."
