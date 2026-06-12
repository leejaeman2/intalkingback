from typing import Literal, Union, Annotated
from ninja import Schema
from ninja.orm import create_schema
from pydantic import EmailStr, Field
from account.models import IntalkingUser

class SigninSchema(Schema):
  email: EmailStr
  password: str

class VerifyCodeSchema(Schema):
  code: str

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
class EditFanSchema(Schema):
  nickname: str | None = None
  phone: str | None = None
  hobby: str | None = None
  food: str | None = None
  mbti: str | None = None
class EditInflSchema(Schema):
  nickname: str | None = None
  phone: str | None = None
  bank: str | None = None
  account: str | None = None
  hobby: str | None = None
  food: str | None = None
  mbti: str | None = None
  info: str | None = None
InflSchema = create_schema(IntalkingUser, exclude=['password', 'is_staff', 'is_superuser',
  'groups', 'user_permissions', 'last_login', 'account', 'bank', 'charnum', 'code', 'date_joined',
  'id', 'is_active', 'point', 'phone', 'last_name', 'first_name'])
_AUTH_EXCLUDE = ['password', 'is_staff', 'is_superuser',
  'groups', 'user_permissions', 'last_login']
_PHOTO_FIELDS = ['photo1', 'photo2', 'photo3', 'photo4',
  'photo5', 'photo6', 'photo7', 'photo8']

# 팬: photo 미사용 → 응답에서 제외
FanMeSchema = create_schema(IntalkingUser, name='FanMeSchema',
  exclude=_AUTH_EXCLUDE + _PHOTO_FIELDS,
  custom_fields=[('fan', Literal['FAN'], 'FAN')])

# 인플: photo1 필수
InflMeSchema = create_schema(IntalkingUser, name='InflMeSchema',
  exclude=_AUTH_EXCLUDE,
  custom_fields=[('fan', Literal['INFL'], 'INFL')])

# fan 값으로 분기 (discriminated union)
MeSchema = Annotated[Union[FanMeSchema, InflMeSchema], Field(discriminator='fan')]

# islogin/ 등 기존 호환용
IntalkingUserSchema = create_schema(IntalkingUser, exclude=_AUTH_EXCLUDE)

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

class InflWithNoticeSchema(Schema):
  email: str
  username: str
  nickname: str | None = None
  fan: str
  hobby: str | None = None
  food: str | None = None
  mbti: str | None = None
  info: str | None = None
  callmode: bool = True
  photo1: str | None = None
  photo2: str | None = None
  photo3: str | None = None
  photo4: str | None = None
  photo5: str | None = None
  photo6: str | None = None
  photo7: str | None = None
  photo8: str | None = None
  has_fanmeeting: bool = False
  has_party: bool = False
  fanmeeting_id: int | None = None
  party_id: int | None = None
