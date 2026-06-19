class HandoffJobConflictError(Exception):
    code = "handoff_job.conflict"
    msg = "Handoff job conflicts with existing data constraints."


class HandoffJobNotFoundError(Exception):
    code = "handoff_job.not_found"
    msg = "Handoff job not found."


class JobArtifactConflictError(Exception):
    code = "job_artifact.conflict"
    msg = "Job artifact conflicts with existing data constraints."


class JobEventConflictError(Exception):
    code = "job_event.conflict"
    msg = "Job event conflicts with existing data constraints."
