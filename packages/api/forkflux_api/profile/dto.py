from dataclasses import dataclass


@dataclass(slots=True)
class ProfileCreate:
    is_onboarded: bool
