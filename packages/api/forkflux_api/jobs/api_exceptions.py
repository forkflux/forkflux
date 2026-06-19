from forkflux_api.exceptions import BaseValidationError


class ParentJobValidationError(BaseValidationError):
    code = "parent_job.invalid"
    msg = "Parent job is invalid."


class TargetRoleValidationError(BaseValidationError):
    code = "target_role.invalid"
    msg = "Target role is invalid."


class HandoffJobClaimValidationError(BaseValidationError):
    code = "handoff_job_claim.invalid"
    msg = "Handoff job claim is invalid."


class HandoffJobIdentityValidationError(BaseValidationError):
    code = "handoff_job_identity.invalid"
    msg = "Handoff job identity is invalid."


class HandoffJobStatusValidationError(BaseValidationError):
    code = "handoff_job_status.invalid"
    msg = "Handoff job status transition is invalid."
