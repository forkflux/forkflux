from pydantic import BaseModel, ConfigDict


class GetProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_onboarded: bool


class CreateProfileRequest(BaseModel):
    is_onboarded: bool


class CreateProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_onboarded: bool
