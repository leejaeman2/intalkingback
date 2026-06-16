import re
from typing import Literal, Union, Annotated
from ninja import Schema
from ninja.orm import create_schema
from pydantic import EmailStr, Field, field_validator
from account.models import IntalkingUser

# 영문 + 숫자 조합, 10자리 이상 (특수기호 허용하되 필수 아님)
PW_RULE = re.compile(r'^(?=.*[A-Za-z])(?=.*\d).{10,}$')

def validate_password(value):
  if not PW_RULE.match(value or ''):
    raise ValueError('비밀번호는 영문과 숫자를 조합해 10자리 이상이어야 합니다.')
  return value

class SigninSchema(Schema):
  email: EmailStr
  password: str
  force: bool = False   # 다른 기기 로그인 경고 후 강제 로그인 여부

class VerifyCodeSchema(Schema):
  code: str

class SignupFanSchema(Schema):
  email: EmailStr
  password: str
  nickname: str
  phone: str
  character: int

  _check_password = field_validator('password')(validate_password)

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

  _check_password = field_validator('password')(validate_password)

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

class LoginErrorSchema(Schema):
  code: str               # NO_USER | WRONG_PASSWORD | LOCKED
  message: str
  fail_count: int = 0
  locked: bool = False

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
