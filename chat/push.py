"""착신 푸시 발송 (앱이 꺼져 있거나 백그라운드일 때 전화 신호 전달)

- iOS: APNs VoIP 푸시 (PushKit → CallKit 수신 화면)
- Android: FCM HTTP v1 high priority data 메시지 (→ 전체화면 수신 알림)
"""
import json
import time
import jwt
import httpx
from channels.db import database_sync_to_async
from django.conf import settings
from account.models import IntalkingUser

_apns_token = {'value': None, 'exp': 0}
_fcm_token = {'value': None, 'exp': 0}
_fcm_account = None


def _apns_auth_token():
  now = time.time()
  if _apns_token['value'] and now < _apns_token['exp']:
    return _apns_token['value']
  with open(settings.APNS_KEY_PATH) as f:
    key = f.read()
  token = jwt.encode({'iss': settings.APNS_TEAM_ID, 'iat': int(now)}, key,
    algorithm='ES256', headers={'kid': settings.APNS_KEY_ID})
  _apns_token.update(value=token, exp=now + 50 * 60)   # APNs 토큰은 20~60분 사이 재발급 권장
  return token


def _load_fcm_account():
  global _fcm_account
  if _fcm_account is None:
    with open(settings.FCM_SERVICE_ACCOUNT_FILE) as f:
      _fcm_account = json.load(f)
  return _fcm_account


async def _fcm_access_token(client):
  now = time.time()
  if _fcm_token['value'] and now < _fcm_token['exp']:
    return _fcm_token['value']
  account = _load_fcm_account()
  assertion = jwt.encode({
    'iss': account['client_email'],
    'scope': 'https://www.googleapis.com/auth/firebase.messaging',
    'aud': 'https://oauth2.googleapis.com/token',
    'iat': int(now), 'exp': int(now) + 3600,
  }, account['private_key'], algorithm='RS256')
  res = await client.post('https://oauth2.googleapis.com/token', data={
    'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
    'assertion': assertion,
  })
  res.raise_for_status()
  body = res.json()
  _fcm_token.update(value=body['access_token'], exp=now + body.get('expires_in', 3600) - 300)
  return _fcm_token['value']


async def _send_apns(token, payload):
  host = 'api.sandbox.push.apple.com' if settings.APNS_USE_SANDBOX else 'api.push.apple.com'
  async with httpx.AsyncClient(http2=True, timeout=10) as client:
    res = await client.post(f'https://{host}/3/device/{token}', json=payload, headers={
      'authorization': f'bearer {_apns_auth_token()}',
      'apns-topic': f'{settings.APNS_BUNDLE_ID}.voip',
      'apns-push-type': 'voip',
      'apns-priority': '10',
      'apns-expiration': '0',   # 전화는 즉시 전달 못 하면 폐기
    })
  if res.status_code == 200:
    return True, False
  reason = ''
  try:
    reason = res.json().get('reason', '')
  except ValueError:
    pass
  print(f'[PUSH] APNs 실패 {res.status_code} {reason}')
  invalid = res.status_code == 410 or reason in ('BadDeviceToken', 'Unregistered', 'DeviceTokenNotForTopic')
  return False, invalid


async def _send_fcm(token, data):
  async with httpx.AsyncClient(timeout=10) as client:
    access = await _fcm_access_token(client)
    project_id = _load_fcm_account()['project_id']
    res = await client.post(
      f'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send',
      headers={'Authorization': f'Bearer {access}'},
      json={'message': {
        'token': token,
        'data': {k: str(v) for k, v in data.items() if v is not None},
        'android': {'priority': 'HIGH', 'ttl': '30s'},
      }},
    )
  if res.status_code == 200:
    return True, False
  print(f'[PUSH] FCM 실패 {res.status_code} {res.text[:300]}')
  invalid = res.status_code == 404 or 'UNREGISTERED' in res.text
  return False, invalid


@database_sync_to_async
def get_push_target(email):
  return IntalkingUser.objects.filter(email=email).values('callmode', 'push_platform', 'push_token').first()


@database_sync_to_async
def _clear_push_token(email, token):
  IntalkingUser.objects.filter(email=email, push_token=token).update(push_token=None, push_platform=None)


async def send_call_push(target, data):
  """target: get_push_target 결과 + email. data: 문자열 값 dict (type=call|cancel)
  성공 여부 반환. 만료된 토큰이면 DB에서 지움."""
  platform, token = target.get('push_platform'), target.get('push_token')
  if not token:
    return False
  try:
    if platform == 'ios':
      if not (settings.APNS_KEY_PATH and settings.APNS_KEY_ID and settings.APNS_TEAM_ID and settings.APNS_BUNDLE_ID):
        print('[PUSH] APNs 설정 없음')
        return False
      ok, invalid = await _send_apns(token, {'aps': {}, **data})
    elif platform == 'android':
      if not settings.FCM_SERVICE_ACCOUNT_FILE:
        print('[PUSH] FCM 설정 없음')
        return False
      ok, invalid = await _send_fcm(token, data)
    else:
      return False
  except Exception as e:
    print(f'[PUSH] 발송 오류 {platform}: {e!r}')
    return False
  if invalid:
    await _clear_push_token(target['email'], token)
  return ok
