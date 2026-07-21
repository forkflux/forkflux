from forkflux_api.exceptions import BaseValidationError


class ProfileAlreadyExistsValidationError(BaseValidationError):
    code = "profile.already_exists"
    msg = "Profile already exists."
