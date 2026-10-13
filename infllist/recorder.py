"""통화 녹음 서버 (aiortc)

각 참여자 앱이 통화 중인 마이크 트랙을 서버에도 별도 PeerConnection 으로 보낸다
(마이크를 새로 열지 않으므로 휴대폰 에코 제거가 깨지지 않음).
서버는 room 단위로 두 트랙을 같은 서버 시계 기준 PCM 임시 파일로 받아 두었다가
양쪽이 끝나면 하나로 섞어 mp3 로 인코딩 → CallRecording.merged (S3) 에 저장한다.

PeerConnection 은 Daphne 이벤트 루프(프로세스 메모리)에 살아 있으므로 단일 프로세스 전제.
"""
import asyncio
import os
import tempfile

import av
import numpy as np
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamError
from django.core.files import File as DjangoFile
from django.db import close_old_connections

from chat.turn import make_turn_credentials

RATE = 16000                      # 음성 녹음용 16kHz 모노
GAP_FILL_SEC = 0.3                # 이보다 길게 프레임이 끊기면(무음 DTX/패킷 손실) 그만큼 무음으로 채움
JOIN_GRACE_SEC = 15               # 한쪽만 끝났을 때 상대 트랙 도착을 기다리는 시간
MAX_CALL_SEC = 4 * 3600           # 비정상 세션 강제 종료
MP3_BITRATE = 32000

sessions = {}                     # room → RecordingSession


def _log(*args):
  print('[REC]', *args)


def _ice_config():
  servers = [RTCIceServer(urls='stun:stun.l.google.com:19302')]
  if os.getenv('TURN_REALM') and os.getenv('TURN_AUTH_SECRET'):
    cred = make_turn_credentials('recorder')
    # aioice 는 turns(TLS) 미지원 → udp/tcp 만
    urls = [u for u in cred['urls'] if u.startswith('turn:')]
    servers.append(RTCIceServer(urls=urls, username=cred['username'], credential=cred['password']))
  return RTCConfiguration(iceServers=servers)


class Participant:
  def __init__(self, session, role):
    self.session = session
    self.role = role
    self.pc = None
    fd, self.path = tempfile.mkstemp(prefix=f'rec_{role}_', suffix='.pcm')
    self.file = os.fdopen(fd, 'wb')
    self.start_sample = None      # 세션 시작 기준 첫 프레임 위치
    self.t_start = None
    self.written = 0              # 기록한 샘플 수
    self.done = asyncio.Event()
    self.task = None

  def write(self, samples):
    self.file.write(samples.tobytes())
    self.written += len(samples)

  async def consume(self, track):
    loop = asyncio.get_running_loop()
    resampler = av.AudioResampler(format='s16', layout='mono', rate=RATE)
    try:
      while True:
        frame = await track.recv()
        now = loop.time()
        if self.t_start is None:
          self.t_start = now
          self.start_sample = int((now - self.session.t0) * RATE)
          _log(f'{self.session.room} {self.role} first audio')
        for out in resampler.resample(frame):
          samples = out.to_ndarray().reshape(-1)
          # 벽시계상 위치보다 크게 뒤처졌으면 끊긴 구간을 무음으로 채워 상대 트랙과 싱크 유지
          behind = int((now - self.t_start) * RATE) - self.written - len(samples)
          if behind > GAP_FILL_SEC * RATE:
            self.write(np.zeros(behind, dtype=np.int16))
          self.write(samples)
    except MediaStreamError:
      pass
    except Exception as e:
      _log(f'{self.session.room} {self.role} consume error: {e!r}')
    finally:
      self.file.close()
      self.done.set()
      _log(f'{self.session.room} {self.role} ended, {self.written / RATE:.1f}s')
      self.session.on_participant_done()

  async def close(self):
    if self.pc:
      await self.pc.close()


class RecordingSession:
  def __init__(self, room, fan_id, infl_id):
    self.room = room
    self.fan_id = fan_id
    self.infl_id = infl_id
    self.t0 = asyncio.get_running_loop().time()
    self.participants = {}        # role → Participant
    self.finalizing = False
    self.watchdog = asyncio.create_task(self._watchdog())

  async def _watchdog(self):
    await asyncio.sleep(MAX_CALL_SEC)
    _log(f'{self.room} max duration reached, closing')
    await self.stop_all()

  async def stop_all(self):
    for p in list(self.participants.values()):
      await p.close()

  async def add(self, role, offer_sdp):
    if role in self.participants:
      raise ValueError('이미 녹음 중인 참여자입니다')
    part = Participant(self, role)
    self.participants[role] = part
    pc = RTCPeerConnection(_ice_config())
    part.pc = pc

    @pc.on('track')
    def on_track(track):
      if track.kind == 'audio' and part.task is None:
        part.task = asyncio.create_task(part.consume(track))

    @pc.on('connectionstatechange')
    async def on_state():
      _log(f'{self.room} {role} pc {pc.connectionState}')
      if pc.connectionState in ('failed', 'closed'):
        await pc.close()
        if part.task is None:     # 트랙이 한 번도 안 옴 → 종료 처리
          part.file.close()
          part.done.set()
          self.on_participant_done()

    await pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type='offer'))
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)   # aiortc 는 ICE 수집 완료 후 반환 (non-trickle)
    return pc.localDescription

  def on_participant_done(self):
    if self.finalizing:
      return
    if all(p.done.is_set() for p in self.participants.values()):
      asyncio.create_task(self._finalize_after_grace())

  async def _finalize_after_grace(self):
    # 상대 쪽 녹음 연결이 늦게 붙는 경우 대비
    if len(self.participants) < 2:
      await asyncio.sleep(JOIN_GRACE_SEC)
    if self.finalizing or not all(p.done.is_set() for p in self.participants.values()):
      return
    self.finalizing = True
    self.watchdog.cancel()
    sessions.pop(self.room, None)
    try:
      await asyncio.to_thread(self._finalize_sync)
    except Exception as e:
      _log(f'{self.room} finalize error: {e!r}')
    finally:
      for p in self.participants.values():
        if os.path.exists(p.path):
          os.remove(p.path)

  def _finalize_sync(self):
    parts = [p for p in self.participants.values() if p.start_sample is not None and p.written > 0]
    if not parts:
      _log(f'{self.room} no audio, skip')
      return
    fd, mp3_path = tempfile.mkstemp(prefix='rec_', suffix='.mp3')
    os.close(fd)
    try:
      total = mix_to_mp3(
        [(p.start_sample, np.memmap(p.path, dtype=np.int16, mode='r')) for p in parts], mp3_path)
      self._save(mp3_path, total // RATE)
      _log(f'{self.room} saved {total / RATE:.1f}s mp3 ({len(parts)} tracks)')
    finally:
      os.remove(mp3_path)
      close_old_connections()

  def _save(self, mp3_path, duration):
    from infllist.models import CallRecording
    rec, _ = CallRecording.objects.get_or_create(
      room=self.room, defaults={'fan_id': self.fan_id, 'infl_id': self.infl_id})
    with open(mp3_path, 'rb') as f:
      rec.merged.save(f'{self.room}.mp3', DjangoFile(f), save=False)
    rec.duration = max(rec.duration, duration)
    rec.save()


def mix_to_mp3(tracks, out_path, block=RATE * 10):
  """tracks: [(시작 샘플 위치, int16 배열)] → 겹쳐 섞어 mp3 저장. 총 샘플 수 반환"""
  # 맨 앞 무음 제거 (먼저 붙은 쪽 시작 기준)
  base = min(start for start, _ in tracks)
  tracks = [(start - base, data) for start, data in tracks]
  total = max(start + len(data) for start, data in tracks)

  container = av.open(out_path, mode='w', format='mp3')
  stream = container.add_stream('libmp3lame', rate=RATE, layout='mono')
  stream.bit_rate = MP3_BITRATE
  for pos in range(0, total, block):
    end = min(pos + block, total)
    acc = np.zeros(end - pos, dtype=np.int32)
    for start, data in tracks:
      lo, hi = max(pos, start), min(end, start + len(data))
      if lo < hi:
        acc[lo - pos:hi - pos] += data[lo - start:hi - start]
    frame = av.AudioFrame.from_ndarray(
      np.clip(acc, -32768, 32767).astype(np.int16).reshape(1, -1), format='s16', layout='mono')
    frame.sample_rate = RATE
    for packet in stream.encode(frame):
      container.mux(packet)
  for packet in stream.encode(None):
    container.mux(packet)
  container.close()
  return total


async def start(room, role, fan_id, infl_id, offer_sdp):
  session = sessions.get(room)
  if session is None:
    session = sessions[room] = RecordingSession(room, fan_id, infl_id)
  elif (session.fan_id, session.infl_id) != (fan_id, infl_id):
    raise ValueError('통화 참여자가 일치하지 않습니다')
  return await session.add(role, offer_sdp)


async def stop(room, role):
  session = sessions.get(room)
  part = session and session.participants.get(role)
  if part:
    await part.close()
