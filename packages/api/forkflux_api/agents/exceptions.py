class AgentApiTokenNotFoundError(Exception):
    code = "agent_api_token.not_found"
    msg = "Agent API token not found."


class AgentApiTokenConflictError(Exception):
    code = "agent_api_token.conflict"
    msg = "Agent API token conflicts with existing data constraints."


class AgentIdentityNotFoundError(Exception):
    code = "agent_identity.not_found"
    msg = "Agent identity not found."


class AgentIdentityConflictError(Exception):
    code = "agent_identity.conflict"
    msg = "Agent identity conflicts with existing data constraints."


class AgentIdentityRoleConflictError(Exception):
    code = "agent_identity_role.conflict"
    msg = "Agent identity role assignment conflicts with existing data constraints."


class AgentIdentityRoleNotFoundError(Exception):
    code = "agent_identity_role.not_found"
    msg = "Agent identity role assignment not found."


class TargetRoleConflictError(Exception):
    code = "target_role.conflict"
    msg = "Target role already exists."


class TargetRoleInUseError(Exception):
    code = "target_role.in_use"
    msg = "Target role is in use and cannot be deleted."


class TargetRoleNotFoundError(Exception):
    code = "target_role.not_found"
    msg = "Target role not found."
