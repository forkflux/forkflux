from fastapi import APIRouter, Depends
from fastapi import status as http_status

from forkflux_api.profile.api_exceptions import ProfileAlreadyExistsValidationError
from forkflux_api.profile.dependencies import get_profile_service
from forkflux_api.profile.dto import ProfileCreate
from forkflux_api.profile.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from forkflux_api.profile.services import ProfileService
from forkflux_api.profile.ui_schemas import CreateProfileRequest, CreateProfileResponse, GetProfileResponse

router = APIRouter(prefix="/profile", tags=["ui"])


@router.get("", response_model=GetProfileResponse)
async def get_profile(service: ProfileService = Depends(get_profile_service)):
    try:
        is_onboarded = await service.get_profile()
    except ProfileNotFoundError:
        is_onboarded = False
    return GetProfileResponse(is_onboarded=is_onboarded)


@router.post("", response_model=CreateProfileResponse, status_code=http_status.HTTP_201_CREATED)
async def create_profile(
    profile_data: CreateProfileRequest,
    service: ProfileService = Depends(get_profile_service),
):
    dto = ProfileCreate(is_onboarded=profile_data.is_onboarded)
    try:
        profile = await service.create(dto)
    except ProfileAlreadyExistsError as err:
        raise ProfileAlreadyExistsValidationError(
            field_name="is_onboarded", value=profile_data.is_onboarded, loc="body", detail=err.msg
        )
    return profile
