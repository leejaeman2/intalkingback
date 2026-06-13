import os
import shutil
import subprocess
import tempfile
from ninja import Router, File, Form
from ninja.files import UploadedFile
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from django.core.files import File as DjangoFile
from account.models import IntalkingUser
from infllist.models import InflList, CallRecording
from infllist.schema import (
  AddInflSchema, InflListOutputSchema, CallEndSchema, FanListOutputSchema,
)

router = Router()


def _field_to_tempfile(field, suffix):
  """스토리지(로컬/S3) 무관하게 FileField 내용을 임시 파일로 복사."""
  fd, path = tempfile.mkstemp(suffix=suffix)
  with os.fdopen(fd, 'wb') as out:
    field.open('rb')
    for chunk in field.chunks():
      out.write(chunk)
    field.close()
  return path


def _try_merge(rec):
  """양쪽 트랙이 모두 도착했고 ffmpeg가 있으면 병합 → merged 저장 후 개별 트랙 삭제."""
  if rec.merged:
    return True
  if not (rec.fan_track and rec.infl_track):
    return False
  ffmpeg = shutil.which('ffmpeg')
  if not ffmpeg:
    # ffmpeg 미설치 시 개별 트랙은 보존하고 병합만 보류
    return False

  fan_tmp = infl_tmp = out_path = None
  try:
    fan_tmp = _field_to_tempfile(rec.fan_track, '.wav')
    infl_tmp = _field_to_tempfile(rec.infl_track, '.wav')
    out_fd, out_path = tempfile.mkstemp(suffix='.m4a')
    os.close(out_fd)
    subprocess.run([
      ffmpeg, '-y',
      '-i', fan_tmp, '-i', infl_tmp,
      '-filter_complex', 'amix=inputs=2:duration=longest:normalize=0',
      '-c:a', 'aac', out_path,
    ], check=True, capture_output=True, timeout=180)
    with open(out_path, 'rb') as f:
      rec.merged.save(f'merged_{rec.room}.m4a', DjangoFile(f), save=False)
    rec.save()
    # 병합 성공 시 개별 트랙 제거 (서버 저장공간 최소화)
    rec.fan_track.delete(save=False)
    rec.infl_track.delete(save=False)
    rec.save()
    return True
  except Exception:
    return False
  finally:
    for p in (fan_tmp, infl_tmp, out_path):
      if p and os.path.exists(p):
        os.remove(p)


@router.post('recording/', response={200: dict})
def upload_recording(request,
  track: UploadedFile = File(...),
  room: str = Form(...),
  role: str = Form(...),
  peer_email: str = Form(...),
  duration: int = Form(0),
):
  me = request.auth
  peer = IntalkingUser.objects.filter(email=peer_email).first()
  if role == 'fan':
    fan, infl = me, peer
  else:
    fan, infl = peer, me

  rec, _ = CallRecording.objects.get_or_create(
    room=room, defaults={'fan': fan, 'infl': infl})
  if rec.fan_id is None and fan:
    rec.fan = fan
  if rec.infl_id is None and infl:
    rec.infl = infl

  if role == 'fan':
    rec.fan_track.save(f'fan_{track.name}', track, save=False)
  else:
    rec.infl_track.save(f'infl_{track.name}', track, save=False)
  rec.duration = max(rec.duration, duration or 0)
  rec.save()

  merged = _try_merge(rec)
  return {'message': '녹음이 업로드되었습니다', 'room': room, 'merged': bool(merged)}

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
