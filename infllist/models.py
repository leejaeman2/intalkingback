from django.core.files.storage import storages
from django.db import models
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
  last = models.DateTimeField(auto_now=True)
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ['created_at']
    unique_together = ['fan', 'infl']

  def __str__(self):
    return f'{self.fan.email} -> {self.infl.email}'

  @classmethod
  def add_infl(cls, fan, infl, duration=0):
    existing = cls.objects.filter(fan=fan, infl=infl).first()
    if existing:
      existing.duration = duration
      existing.save(update_fields=['duration', 'last'])
      return existing

    if cls.objects.filter(fan=fan).count() >= 5:
      cls.objects.filter(fan=fan).order_by('created_at').first().delete()

    return cls.objects.create(fan=fan, infl=infl, duration=duration)

  @classmethod
  def add_call_record(cls, fan, infl, duration=0):
    existing = cls.objects.filter(fan=fan, infl=infl).first()
    if existing:
      existing.duration = duration
      existing.save(update_fields=['duration', 'last'])
      return existing

    if cls.objects.filter(fan=fan).count() >= 5:
      cls.objects.filter(fan=fan).order_by('created_at').first().delete()

    if cls.objects.filter(infl=infl).count() >= 5:
      cls.objects.filter(infl=infl).order_by('created_at').first().delete()

    return cls.objects.create(fan=fan, infl=infl, duration=duration)
