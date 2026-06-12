from ninja import Router
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from account.models import IntalkingUser
from infllist.models import InflList
from infllist.schema import (
  AddInflSchema, InflListOutputSchema, CallEndSchema, FanListOutputSchema,
)

router = Router()

@router.post('add/', response={200: dict})
def add_infl(request, payload: AddInflSchema):
  fan = request.auth
  infl = get_object_or_404(IntalkingUser, email=payload.infl_email, fan='INFL')
  InflList.add_infl(fan=fan, infl=infl)
  return {'message': '인플루언서가 목록에 추가되었습니다'}

@router.get('list/', response=list[InflListOutputSchema])
def get_infl_list(request):
  items = InflList.objects.filter(fan=request.auth).select_related('infl').order_by('-last')
  return [
    {
      'id': item.id,
      'fan_email': item.fan.email,
      'infl_email': item.infl.email,
      'infl_nickname': item.infl.nickname,
      'infl_photo1': item.infl.photo1.url if item.infl.photo1 else None,
      'duration': item.duration,
      'last': str(item.last),
      'created_at': str(item.created_at),
    }
    for item in items
  ]

@router.get('fans/', response=list[FanListOutputSchema])
def get_fan_list(request):
  items = InflList.objects.filter(infl=request.auth).select_related('fan').order_by('-last')
  return [
    {
      'id': item.id,
      'fan_email': item.fan.email,
      'fan_nickname': item.fan.nickname,
      'fan_photo1': item.fan.photo1.url if item.fan.photo1 else None,
      'duration': item.duration,
      'last': str(item.last),
      'created_at': str(item.created_at),
    }
    for item in items
  ]

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
  return {'message': '통화 기록이 저장되었습니다'}
