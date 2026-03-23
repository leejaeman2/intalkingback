from ninja import Router
from django.shortcuts import get_object_or_404
from account.models import IntalkingUser
from infllist.models import InflList
from infllist.schema import AddInflSchema, InflListOutputSchema

router = Router()

@router.post('add/', response={200: dict})
def add_infl(request, payload: AddInflSchema):
  fan = request.user
  infl = get_object_or_404(IntalkingUser, email=payload.infl_email, fan='INFL')
  InflList.add_infl(fan=fan, infl=infl)
  return {'message': '인플루언서가 목록에 추가되었습니다'}

@router.get('list/', response=list[InflListOutputSchema])
def get_infl_list(request):
  items = InflList.objects.filter(fan=request.user).select_related('infl')
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
