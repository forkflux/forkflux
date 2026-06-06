class AgentApiTokenNotFoundError(Exception):
    code = "agent_api_token.not_found"
    msg = "Agent API token not found."


class AgentIdentityNotFoundError(Exception):
    code = "agent_identity.not_found"
    msg = "Agent identity not found."
