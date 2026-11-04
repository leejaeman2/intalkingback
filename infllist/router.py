import calendar
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from ninja import Router
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from account.models import IntalkingUser
from infllist.models import InflList, InflBlock, CallSettle
from infllist.schema import (
  AddInflSchema, InflListOutputSchema, CallEndSchema, FanListOutputSchema, FanDetailOutputSchema, FanMemoSchema, FanBlockSchema,
  RecordingOfferSchema, RecordingAnswerSchema, RecordingStopSchema, SettleOutputSchema,
)
from infllist import recorder

router = Router()


# 통화 녹음: 앱이 통화 마이크 트랙을 서버(aiortc)로도 보냄 → 통화 종료 시 mp3 로 S3 저장
@router.post('recording/offer/', response={200: RecordingAnswerSchema})
async def recording_offer(request, payload: RecordingOfferSchema):
  me = request.auth
  peer = await IntalkingUser.objects.filter(email=payload.peer_email).afirst()
  if not peer:
    raise HttpError(404, '상대 사용자를 찾을 수 없습니다')
  if me.fan == 'FAN' and peer.fan == 'INFL':
    role, fan_id, infl_id = 'fan', me.id, peer.id
  elif me.fan == 'INFL' and peer.fan == 'FAN':
    role, fan_id, infl_id = 'infl', peer.id, me.id
  else:
    raise HttpError(400, '잘못된 통화 관계입니다')
  try:
    answer = await recorder.start(payload.room, role, fan_id, infl_id, payload.sdp)
  except ValueError as e:
    raise HttpError(409, str(e))
  return {'sdp': answer.sdp, 'type': answer.type}

@router.post('recording/stop/', response={200: dict})
async def recording_stop(request, payload: RecordingStopSchema):
  role = 'infl' if request.auth.fan == 'INFL' else 'fan'
  await recorder.stop(payload.room, role)
  return {'message': '녹음이 종료되었습니다'}

@router.post('add/', response={200: dict})
def add_infl(request, payload: AddInflSchema):
  fan = request.auth
  infl = get_object_or_404(IntalkingUser, email=payload.infl_email, fan='INFL')
  InflList.add_infl(fan=fan, infl=infl)
  return {'message': '인플루언서가 목록에 추가되었습니다'}

@router.get('list/', response=list[InflListOutputSchema])
def get_infl_list(request):
  items = InflList.objects.filter(fan=request.auth).select_related('infl').order_by('-last')[:InflList.MAX_PER_FAN]
  return [
    {
      'id': item.id,
      'fan_email': item.fan.email,
      'infl_email': item.infl.email,
      'infl_nickname': item.infl.nickname,
      'infl_photo1': item.infl.photo1.url if item.infl.photo1 else None,
      'infl_callmode': item.infl.callmode,
      'duration': item.duration,
      'last': str(item.last),
      'created_at': str(item.created_at),
    }
    for item in items
  ]

@router.delete('delete/{item_id}/', response={200: dict})
def delete_infl(request, item_id: int):
  item = get_object_or_404(InflList, id=item_id, fan=request.auth)
  item.delete()
  return {'message': '인플루언서가 목록에서 삭제되었습니다'}

@router.get('fans/', response=list[FanListOutputSchema])
def get_fan_list(request):
  items = InflList.objects.filter(infl=request.auth).select_related('fan').order_by('-last')
  blocked_ids = set(InflBlock.objects.filter(infl=request.auth).values_list('fan_id', flat=True))
  return [
    {
      'id': item.id,
      'fan_email': item.fan.email,
      'fan_nickname': item.fan.nickname,
      'fan_photo1': item.fan.photo1.url if item.fan.photo1 else None,
      'fan_charnum': item.fan.charnum,
      'blocked': item.fan_id in blocked_ids,
      'duration': item.duration,
      'last': str(item.last),
      'created_at': str(item.created_at),
    }
    for item in items
  ]

# 내 팬(InflList 관계가 있는 팬)만 조회 가능. 연락처/포인트 등 민감 정보는 제외
@router.get('fans/detail/', response=FanDetailOutputSchema)
def get_fan_detail(request, email: str):
  item = get_object_or_404(InflList.objects.select_related('fan'), infl=request.auth, fan__email=email)
  fan = item.fan
  return {
    'email': fan.email,
    'nickname': fan.nickname,
    'charnum': fan.charnum,
    'photo1': fan.photo1.url if fan.photo1 else None,
    'hobby': fan.hobby,
    'food': fan.food,
    'mbti': fan.mbti,
    'birth': str(fan.birth) if fan.birth else None,
    'memo': item.memo,
    'duration': item.duration,
    'last': str(item.last),
    'created_at': str(item.created_at),
  }

# update_fields 로 memo 만 저장 → last(auto_now) 가 갱신되지 않아 최근 통화 정렬 유지
@router.patch('fans/memo/', response={200: dict})
def update_fan_memo(request, payload: FanMemoSchema):
  item = get_object_or_404(InflList, infl=request.auth, fan__email=payload.email)
  item.memo = payload.memo.strip()
  item.save(update_fields=['memo'])
  return {'message': '메모가 저장되었습니다', 'memo': item.memo}

# 차단 토글. 내 팬(InflList 관계가 있는 팬)만 차단 가능, 해제는 관계가 사라져도 가능
@router.post('fans/block/', response={200: dict})
def toggle_fan_block(request, payload: FanBlockSchema):
  block = InflBlock.objects.filter(infl=request.auth, fan__email=payload.email).first()
  if block:
    block.delete()
    return {'blocked': False}
  item = get_object_or_404(InflList, infl=request.auth, fan__email=payload.email)
  InflBlock.objects.get_or_create(infl=request.auth, fan=item.fan)
  return {'blocked': True}

@router.post('call-end/', response={200: dict})
def call_end(request, payload: CallEndSchema):
  me = request.auth
  peer = get_object_or_404(IntalkingUser, email=payload.peer_email)

  if me.fan == 'FAN' and peer.fan == 'INFL':
    fan, infl = me, peer
  elif me.fan == 'INFL' and peer.fan == 'FAN':
    fan, infl = peer, me
  else:
    raise HttpError(400, '잘못된 통화 관계입니다')

  InflList.add_call_record(fan=fan, infl=infl, duration=payload.duration)
  if payload.room:
    CallSettle.objects.filter(room=payload.room, fan=fan, infl=infl).update(duration=payload.duration)
  return {'message': '통화 기록이 저장되었습니다'}

KST = ZoneInfo('Asia/Seoul')

# 인플 정산 내역: 기간(start~end, KST 날짜) 내 통화 정산을 월별로 묶어 반환
@router.get('settle/', response=SettleOutputSchema)
def get_settle(request, start: date, end: date):
  if request.auth.fan != 'INFL':
    raise HttpError(403, '인플루언서만 조회할 수 있습니다')
  if start > end:
    raise HttpError(400, '시작일이 종료일보다 늦습니다')

  since = datetime.combine(start, time.min, tzinfo=KST)
  until = datetime.combine(end + timedelta(days=1), time.min, tzinfo=KST)
  settles = CallSettle.objects.filter(infl=request.auth, created_at__gte=since, created_at__lt=until)

  months = {}
  for s in settles:   # ordering: -created_at → 최근 월/통화가 위로
    at = s.created_at.astimezone(KST)
    key = (at.year, at.month)
    if key not in months:
      last_day = calendar.monthrange(at.year, at.month)[1]
      months[key] = {
        'year': at.year, 'month': at.month,
        'start': str(max(start, date(at.year, at.month, 1))),
        'end': str(min(end, date(at.year, at.month, last_day))),
        'total': 0, 'items': [],
      }
    months[key]['total'] += s.infl_amount
    months[key]['items'].append({
      'id': s.id, 'fan_nickname': s.fan_nickname,
      'created_at': at.strftime('%Y-%m-%d %H:%M'),
      'duration': s.duration, 'amount': s.infl_amount,
    })

  return {'total': sum(m['total'] for m in months.values()), 'months': list(months.values())}
