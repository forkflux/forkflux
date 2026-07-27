class HandoffJobConflictError(Exception):
    code = "handoff_job.conflict"
    msg = "Handoff job conflicts with existing data constraints."


class HandoffJobNotFoundError(Exception):
    code = "handoff_job.not_found"
    msg = "Handoff job not found."

    def __init__(self, which: str | None = None):
        # ``which`` lets callers (e.g. HandoffJobService.reject_job) tag which
        # job identifier was not found so handlers can attribute the error to
        # the correct field. Defaults to None to preserve all existing bare
        # ``raise HandoffJobNotFoundError`` call sites. It is kept as metadata
        # only; the base exception always carries the generic ``msg`` so
        # ``str(err)`` describes the failure rather than the field name.
        self.which = which
        super().__init__(self.msg)


class HandoffJobHasChildrenError(Exception):
    code = "handoff_job.has_children"
    msg = "Handoff job cannot be deleted because it has child jobs."


class JobArtifactConflictError(Exception):
    code = "job_artifact.conflict"
    msg = "Job artifact conflicts with existing data constraints."


class JobDependencyConflictError(Exception):
    code = "job_dependency.conflict"
    msg = "Job dependency conflicts with existing data constraints."


class JobEventConflictError(Exception):
    code = "job_event.conflict"
    msg = "Job event conflicts with existing data constraints."
