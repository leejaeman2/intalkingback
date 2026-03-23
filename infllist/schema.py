from ninja import Schema
from pydantic import EmailStr

class AddInflSchema(Schema):
  infl_email: EmailStr

class InflListOutputSchema(Schema):
  id: int
  fan_email: str
  infl_email: str
  infl_nickname: str | None = None
  infl_photo1: str | None = None
  duration: int
  last: str
  created_at: str
