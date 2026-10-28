from ninja import Router
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from notice.models import Notice, NoticeApply
from notice.schema import NoticeOutputSchema

router = Router()

@router.get('list/', response=list[NoticeOutputSchema])
def get_notices(request):
  notices = Notice.objects.filter(is_deleted=False)
  return [
    {
      'id': n.id,
      'author': n.author,
      'type': n.type,
      'title': n.title,
      'content': n.content,
      'event_date': str(n.event_date) if n.event_date else None,
      'created_at': str(n.created_at),
    }
    for n in notices
  ]

@router.get('{int:notice_id}/', response=NoticeOutputSchema)
def get_notice(request, notice_id: int):
  n = get_object_or_404(Notice, id=notice_id, is_deleted=False)
  return {
    'id': n.id,
    'author': n.author,
    'type': n.type,
    'title': n.title,
    'content': n.content,
    'event_date': str(n.event_date) if n.event_date else None,
    'created_at': str(n.created_at),
    'applied': NoticeApply.objects.filter(notice=n, fan=request.auth).exists(),
  }

@router.post('{int:notice_id}/apply/', response={200: dict})
def apply_notice(request, notice_id: int):
  n = get_object_or_404(Notice, id=notice_id, is_deleted=False)
  if n.type not in ('FANMEETING', 'PARTY'):
    raise HttpError(400, '신청할 수 없는 공지입니다')
  if n.is_expired:
    raise HttpError(400, f'이미 종료된 {n.get_type_display()}입니다')
  if request.auth.fan != 'FAN':
    raise HttpError(403, '팬만 신청할 수 있습니다')
  _, created = NoticeApply.objects.get_or_create(notice=n, fan=request.auth)
  if not created:
    raise HttpError(400, f'이미 신청한 {n.get_type_display()}입니다')
  return {'message': f'{n.get_type_display()} 신청이 완료되었습니다'}

@router.delete('{int:notice_id}/apply/', response={200: dict})
def cancel_notice(request, notice_id: int):
  n = get_object_or_404(Notice, id=notice_id, is_deleted=False)
  if n.is_expired:
    raise HttpError(400, f'이미 종료된 {n.get_type_display()}입니다')
  deleted, _ = NoticeApply.objects.filter(notice=n, fan=request.auth).delete()
  if not deleted:
    raise HttpError(400, f'{n.get_type_display()} 신청 내역이 없습니다')
  return {'message': f'{n.get_type_display()} 신청이 취소되었습니다'}
