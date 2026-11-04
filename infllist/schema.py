from ninja import Schema
from pydantic import EmailStr, Field

class AddInflSchema(Schema):
  infl_email: EmailStr

class InflListOutputSchema(Schema):
  id: int
  fan_email: str
  infl_email: str
  infl_nickname: str | None = None
  infl_photo1: str | None = None
  infl_callmode: bool = True
  duration: int
  last: str
  created_at: str

class CallEndSchema(Schema):
  peer_email: EmailStr
  duration: int = 0
  room: str | None = None

class FanListOutputSchema(Schema):
  id: int
  fan_email: str
  fan_nickname: str | None = None
  fan_photo1: str | None = None
  fan_charnum: int | None = None
  blocked: bool = False
  duration: int
  last: str
  created_at: str

class FanDetailOutputSchema(Schema):
  email: str
  nickname: str | None = None
  charnum: int | None = None
  photo1: str | None = None
  hobby: str | None = None
  food: str | None = None
  mbti: str | None = None
  birth: str | None = None
  memo: str = ''
  duration: int
  last: str
  created_at: str

class FanMemoSchema(Schema):
  email: str
  memo: str = Field(max_length=1000)

class FanBlockSchema(Schema):
  email: str

class RecordingOfferSchema(Schema):
  room: str
  peer_email: EmailStr
  sdp: str

class RecordingAnswerSchema(Schema):
  sdp: str
  type: str

class RecordingStopSchema(Schema):
  room: str

class SettleOneSchema(Schema):
  id: int
  fan_nickname: str
  created_at: str          # 'YYYY-MM-DD HH:MM' (KST)
  duration: int
  amount: int              # 인플 적립금

class SettleMonthSchema(Schema):
  year: int
  month: int
  start: str               # 조회 기간과 겹치는 해당 월의 시작/끝 날짜
  end: str
  total: int
  items: list[SettleOneSchema]

class SettleOutputSchema(Schema):
  total: int
  months: list[SettleMonthSchema]
