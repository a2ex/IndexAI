from pydantic import BaseModel


class NotificationSettingsResponse(BaseModel):
    webhook_url: str | None = None
    webhook_enabled: bool = False
    email_digest_enabled: bool = False
    email_digest_address: str | None = None

    model_config = {"from_attributes": True}


class NotificationSettingsUpdate(BaseModel):
    webhook_url: str | None = None
    webhook_enabled: bool = False
    email_digest_enabled: bool = False
    email_digest_address: str | None = None
