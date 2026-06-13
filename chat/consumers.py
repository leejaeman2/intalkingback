import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from account.models import IntalkingUser

online_users = {}


@database_sync_to_async
def get_callmode(email):
  return IntalkingUser.objects.filter(email=email).values_list('callmode', flat=True).first()


class CallConsumer(AsyncWebsocketConsumer):
  async def connect(self):
    self.email = None
    await self.accept()

  async def disconnect(self, close_code):
    if self.email and online_users.get(self.email) == self.channel_name:
      online_users.pop(self.email, None)

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
        await self.send(text_data=json.dumps({'type': 'registered', 'email': new_email}))
      return

    target = data.get('target')
    target_channel = online_users.get(target)

    if msg_type == 'call_request':
      if not target_channel:
        await self.send(text_data=json.dumps({'type': 'call_unavailable', 'target': target}))
        return
      callmode = await get_callmode(target)
      if callmode is False:
        await self.send(text_data=json.dumps({'type': 'call_off', 'target': target}))
        return
      await self.channel_layer.send(target_channel, {
        'type': 'relay',
        'data': {
          'type': 'incoming_call',
          'caller': self.email,
          'nickname': data.get('nickname'),
          'photo1': data.get('photo1'),
          'room': data.get('room'),
        },
      })
      return

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
