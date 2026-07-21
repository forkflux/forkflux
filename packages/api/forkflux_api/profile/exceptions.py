class ProfileNotFoundError(Exception):
    code = "profile.not_found"
    msg = "Profile not found."


class ProfileAlreadyExistsError(Exception):
    code = "profile.already_exists"
    msg = "Profile already exists."
