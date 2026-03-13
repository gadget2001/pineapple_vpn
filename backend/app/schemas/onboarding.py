from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

OnboardingStep = Literal[
    "welcome",
    "trial_offer",
    "device_select",
    "install_app",
    "get_config",
    "complete",
    "done",
]

DeviceOS = Literal["windows", "iphone", "android", "macos"]


class OnboardingStateOut(BaseModel):
    step: OnboardingStep
    step_index: int = Field(ge=1)
    total_steps: int = Field(default=6, ge=1)
    terms_accepted: bool
    terms_accepted_at: datetime | None
    trial_available: bool
    trial_activated_at: datetime | None
    trial_days: int
    os: DeviceOS | None
    install_confirmed: bool
    has_active_subscription: bool
    vpn_ready: bool
    completed: bool
    onboarding_completed_at: datetime | None


class AcceptTermsRequest(BaseModel):
    accepted: bool


class SelectDeviceRequest(BaseModel):
    os: DeviceOS


class InstructionConfirmRequest(BaseModel):
    os: DeviceOS | None = None


class OnboardingInstructionOut(BaseModel):
    os: DeviceOS
    app_name: str
    download_url: str
    steps: list[str]


class OnboardingConfigOut(BaseModel):
    subscription_url: str
    import_help: str


class TrialActivationOut(BaseModel):
    status: str
    ends_at: datetime
    trial_days: int
