import uuid
from datetime import datetime
from pydantic import BaseModel


class CreditBalance(BaseModel):
    balance: int
    user_id: uuid.UUID


class CreditTransactionResponse(BaseModel):
    id: uuid.UUID
    amount: int
    type: str
    description: str | None
    url_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
