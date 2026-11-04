from django.core.files.storage import storages
from django.db import models, transaction
from account.models import IntalkingUser


def recording_storage():
  # settings.STORAGES['recordings'] (운영: S3)
  return storages['recordings']


def recording_path(instance, filename):
  return f'recordings/{instance.room}/{filename}'


def merged_path(instance, filename):
  # filename 은 recorder 가 정함: 2026/10/13/20261013_153012_fan닉네임_infl닉네임.mp3
  return f'recordings/{filename}'


class CallRecording(models.Model):
  """1:1 보이스톡 통화 녹음. 녹음 서버(infllist/recorder.py)가 양쪽 목소리를
  섞은 mp3 를 merged 에 저장한다 (settings.STORAGES['recordings'] → 운영 S3).
  fan_track/infl_track 은 이전 방식(단말 녹음 업로드)의 기존 데이터용."""
  room = models.CharField(max_length=160, unique=True, db_index=True)
  fan = models.ForeignKey(IntalkingUser, on_delete=models.SET_NULL,
    null=True, blank=True, related_name='+')
  infl = models.ForeignKey(IntalkingUser, on_delete=models.SET_NULL,
    null=True, blank=True, related_name='+')
  fan_track = models.FileField(upload_to=recording_path, null=True, blank=True)
  infl_track = models.FileField(upload_to=recording_path, null=True, blank=True)
  merged = models.FileField(upload_to=merged_path, max_length=255, storage=recording_storage, null=True, blank=True)
  duration = models.IntegerField(default=0)
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ['-created_at']

  def __str__(self):
    return f'{self.room} ({self.duration}s)'

class InflList(models.Model):
  fan = models.ForeignKey(IntalkingUser, on_delete=models.CASCADE, related_name='infl_list')
  infl = models.ForeignKey(IntalkingUser, on_delete=models.CASCADE, related_name='fan_list')
  duration = models.IntegerField(default=0)
  memo = models.TextField(blank=True, default='')   # 인플이 팬에 대해 남기는 메모 (인플만 조회/수정)
  last = models.DateTimeField(auto_now=True)
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ['created_at']
    unique_together = ['fan', 'infl']

  def __str__(self):
    return f'{self.fan.email} -> {self.infl.email}'

  MAX_PER_FAN = 5

  @classmethod
  def add_infl(cls, fan, infl, duration=0):
    return cls.add_call_record(fan=fan, infl=infl, duration=duration)

  @classmethod
  def add_call_record(cls, fan, infl, duration=0):
    """통화 완료 시 팬의 '내 인플 보기'에 추가. 팬당 최대 5명,
    6번째 인플이 추가되면 가장 먼저 추가된(created_at) 인플을 삭제한다.
    통화 종료 시 팬/인플 양쪽이 동시에 보고하므로 팬 row 를 잠가 중복 삭제를 막는다."""
    with transaction.atomic():
      IntalkingUser.objects.select_for_update().filter(pk=fan.pk).first()

      existing = cls.objects.filter(fan=fan, infl=infl).first()
      if existing:
        existing.duration = duration
        existing.save(update_fields=['duration', 'last'])
        return existing

      # 새로 추가될 1명 자리를 남기고 오래된 순으로 삭제
      old_ids = list(cls.objects.filter(fan=fan).order_by('-created_at')
        .values_list('id', flat=True)[cls.MAX_PER_FAN - 1:])
      cls.objects.filter(id__in=old_ids).delete()

      return cls.objects.create(fan=fan, infl=infl, duration=duration)


class InflBlock(models.Model):
  """인플이 차단한 팬. 차단된 팬이 전화를 걸면 인플에게 착신 신호를 보내지 않는다.
  InflList 는 팬당 5명 초과 시 자동 삭제되므로 차단 정보는 별도로 보관한다."""
  infl = models.ForeignKey(IntalkingUser, on_delete=models.CASCADE, related_name='blocked_fans')
  fan = models.ForeignKey(IntalkingUser, on_delete=models.CASCADE, related_name='blocked_by')
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    unique_together = ['infl', 'fan']

  def __str__(self):
    return f'{self.infl.email} x {self.fan.email}'


class CallSettle(models.Model):
  """통화 1건의 정산. 팬이 20분 블록(16,000P)을 결제할 때마다 add_charge 로 누적되고,
  배분율은 결제 시점의 인플 등급(is_famous)으로 고정해 이후 등급이 바뀌어도 과거 정산은 그대로 둔다.
  일반 인플 40% / 회사 50% / 영업진 10%, 유명 인플 50% / 회사 40% / 영업진 10%."""
  RATES = {
    False: {'infl': 40, 'company': 50, 'sales': 10},
    True: {'infl': 50, 'company': 40, 'sales': 10},
  }

  room = models.CharField(max_length=160, null=True, blank=True, db_index=True)
  fan = models.ForeignKey(IntalkingUser, on_delete=models.SET_NULL,
    null=True, blank=True, related_name='+')
  infl = models.ForeignKey(IntalkingUser, on_delete=models.SET_NULL,
    null=True, blank=True, related_name='settles')
  fan_nickname = models.CharField(max_length=255, blank=True, default='')   # 팬 탈퇴 후에도 내역 표시용
  is_famous = models.BooleanField(default=False)
  blocks = models.IntegerField(default=0)            # 결제한 20분 블록 수
  amount = models.IntegerField(default=0)            # 팬 결제 총액
  infl_amount = models.IntegerField(default=0)       # 인플 적립금
  company_amount = models.IntegerField(default=0)
  sales_amount = models.IntegerField(default=0)
  duration = models.IntegerField(default=0)          # 통화 시간 (초), call-end 시 갱신
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ['-created_at']

  def __str__(self):
    return f'{self.fan_nickname} -> {self.infl} {self.amount}원'

  @classmethod
  def add_charge(cls, fan, infl, price, room=None):
    """같은 room 의 통화면 기존 정산에 누적, 아니면 새 정산 생성. 호출부의 transaction 안에서 실행."""
    settle = None
    if room:
      settle = cls.objects.select_for_update().filter(room=room, fan=fan, infl=infl).first()
    if not settle:
      settle = cls(room=room, fan=fan, infl=infl, fan_nickname=fan.nickname or '', is_famous=infl.is_famous)

    rate = cls.RATES[settle.is_famous]
    infl_share = price * rate['infl'] // 100
    sales_share = price * rate['sales'] // 100
    settle.blocks += 1
    settle.amount += price
    settle.infl_amount += infl_share
    settle.sales_amount += sales_share
    settle.company_amount += price - infl_share - sales_share   # 나머지(반올림 오차 포함)는 회사
    settle.save()
    return settle
