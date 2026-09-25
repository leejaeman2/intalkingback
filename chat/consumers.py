import json
import time
import uuid
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from chat.push import get_push_target, send_call_push

online_users = {}
background_users = set()   # WS는 붙어 있지만 앱이 백그라운드인 사용자 → 푸시로 착신
pending_calls = {}         # 푸시로 착신 중인 통화 {callee_email: {caller, uuid, room, target, ts}}
PENDING_TTL = 60


class CallConsumer(AsyncWebsocketConsumer):
  async def connect(self):
    self.email = None
    await self.accept()

  async def disconnect(self, close_code):
    if self.email and online_users.get(self.email) == self.channel_name:
      online_users.pop(self.email, None)
      background_users.discard(self.email)

  async def receive(self, text_data=None, bytes_data=None):
    try:
      data = json.loads(text_data)
    except (TypeError, ValueError):
      return

    msg_type = data.get('type')

    if msg_type == 'register':
      new_email = data.get('email')
      if new_email:
        existing_channel = online_users.get(new_email)
        if existing_channel and existing_channel != self.channel_name:
          await self.channel_layer.send(existing_channel, {
            'type': 'relay',
            'data': {'type': 'force_logout', 'reason': '다른 기기에서 로그인되었습니다.'},
          })
        self.email = new_email
        online_users[new_email] = self.channel_name
        if data.get('state') == 'background':
          background_users.add(new_email)
        else:
          background_users.discard(new_email)
        print(f'[WS] register {new_email!r} | online={list(online_users)}')
        await self.send(text_data=json.dumps({'type': 'registered', 'email': new_email}))
      return

    if msg_type == 'app_state':
      if self.email and online_users.get(self.email) == self.channel_name:
        if data.get('state') == 'background':
          background_users.add(self.email)
        else:
          background_users.discard(self.email)
      return

    target = data.get('target')
    target_channel = online_users.get(target)

    if msg_type == 'call_request':
      foreground = bool(target_channel) and target not in background_users
      print(f'[WS] call_request from={self.email!r} target={target!r} '
            f'found={bool(target_channel)} foreground={foreground} | online={list(online_users)}')
      info = await get_push_target(target) if target else None
      if not info:
        await self.send(text_data=json.dumps({'type': 'call_unavailable', 'target': target}))
        return
      if info['callmode'] is False:
        await self.send(text_data=json.dumps({'type': 'call_off', 'target': target}))
        return
      incoming = {
        'type': 'incoming_call',
        'caller': self.email,
        'nickname': data.get('nickname'),
        'photo1': data.get('photo1'),
        'room': data.get('room'),
      }
      if foreground:
        await self.channel_layer.send(target_channel, {'type': 'relay', 'data': incoming})
        return
      # 앱이 꺼져 있거나 백그라운드 → 푸시로 착신 (iOS CallKit / Android 전체화면 알림)
      call_uuid = str(uuid.uuid4())
      pushed = await send_call_push({**info, 'email': target}, {
        **incoming, 'type': 'call', 'uuid': call_uuid, 'callee': target,
      })
      if pushed:
        pending_calls[target] = {'caller': self.email, 'uuid': call_uuid, 'room': data.get('room'),
          'target': {**info, 'email': target}, 'ts': time.time()}
        await self.send(text_data=json.dumps({'type': 'call_ringing', 'target': target}))
      elif target_channel:
        await self.channel_layer.send(target_channel, {'type': 'relay', 'data': incoming})
      else:
        await self.send(text_data=json.dumps({'type': 'call_unavailable', 'target': target}))
      return

    if msg_type in ('call_accept', 'call_reject'):
      pending_calls.pop(self.email, None)

    if msg_type == 'call_end':
      # 발신자가 상대 수신 전에 끊음 → 울리고 있는 착신 화면 닫기
      pending = pending_calls.get(target)
      if pending and pending['caller'] == self.email:
        pending_calls.pop(target, None)
        if time.time() - pending['ts'] < PENDING_TTL:
          await send_call_push(pending['target'], {
            'type': 'cancel', 'uuid': pending['uuid'], 'room': pending['room'] or '', 'caller': self.email,
          })

    if msg_type in ('call_accept', 'call_reject', 'call_end'):
      if target_channel:
        await self.channel_layer.send(target_channel, {
          'type': 'relay',
          'data': {'type': msg_type, 'peer': self.email},
        })
      return

    if msg_type == 'offer':
      if target_channel:
        await self.channel_layer.send(target_channel, {
          'type': 'relay',
          'data': {'type': 'offer', 'peer': self.email, 'offer': data.get('offer')},
        })
      return

    if msg_type == 'answer':
      if target_channel:
        await self.channel_layer.send(target_channel, {
          'type': 'relay',
          'data': {'type': 'answer', 'peer': self.email, 'answer': data.get('answer')},
        })
      return

    if msg_type == 'ice_candidate':
      if target_channel:
        await self.channel_layer.send(target_channel, {
          'type': 'relay',
          'data': {'type': 'ice_candidate', 'peer': self.email, 'candidate': data.get('candidate')},
        })
      return

  async def relay(self, event):
    await self.send(text_data=json.dumps(event['data']))
