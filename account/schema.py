from ninja import Schema
from ninja.orm import create_schema
from pydantic import EmailStr
from account.models import IntalkingUser

class SigninSchema(Schema):
  email: EmailStr
  password: str

SignupFanSchema = create_schema(IntalkingUser, fields=['email'])
SignupInflSchema = create_schema(IntalkingUser, fields=[])
SignupOutputSchema = create_schema(IntalkingUser, fields=[])
EditFanSchema = create_schema(IntalkingUser, fields=['email'])
EditInflSchema = create_schema(IntalkingUser, fields=['email'])
IntalkingUserSchema = create_schema(IntalkingUser, exclude=['password', 'is_staff', 'is_superuser',
  'groups', 'user_permissions', 'last_login'])

class TokenSchema(Schema):
  access: str
  refresh: str
  id: int
  email: str
  nickname: str
  point: int = 0
  photo1: str | None = None

class AccessSchema(Schema):
  access: str

class RefreshSchema(Schema):
  refresh: str

class IsLoginSchema(Schema):
  islogin: bool
