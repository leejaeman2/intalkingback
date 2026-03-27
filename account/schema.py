from ninja import Schema
from ninja.orm import create_schema
from pydantic import EmailStr
from account.models import IntalkingUser

class SigninSchema(Schema):
  email: EmailStr
  password: str

class SignupFanSchema(Schema):
  email: EmailStr
  password: str
  nickname: str
  phone: str
  character: int

class SignupInflSchema(Schema):
  email: EmailStr
  password: str
  nickname: str
  phone: str
  bank: str
  account: str
  code: str
  hobby: str
  food: str
  mbti: str

SignupOutputSchema = create_schema(IntalkingUser, fields=['id', 'email', 'nickname', 'fan'])
EditFanSchema = create_schema(IntalkingUser, fields=['email'])
EditInflSchema = create_schema(IntalkingUser, fields=['email'])
InflSchema = create_schema(IntalkingUser, exclude=['password', 'is_staff', 'is_superuser',
  'groups', 'user_permissions', 'last_login', 'account', 'bank', 'charnum', 'code', 'date_joined',
  'id', 'is_active', 'point', 'phone', 'last_name', 'first_name'])
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
  fan: str

class AccessSchema(Schema):
  access: str

class RefreshSchema(Schema):
  refresh: str

class IsLoginSchema(Schema):
  islogin: bool

class PointChargeSchema(Schema):
  minutes: int
  price: int
