from django.db import models
from account.models import IntalkingUser


def recording_path(instance, filename):
  return f'recordings/{instance.room}/{filename}'


class CallRecording(models.Model):
  """1:1 보이스톡 통화 녹음. 각 참여자가 자기 마이크 트랙을 업로드하고,
  서버에서 두 트랙을 병합해 최종 파일(merged)을 보관한다.
  파일은 Django 기본 스토리지에 저장되므로 EC2 로컬(MEDIA_ROOT) 또는
  django-storages 설정 시 S3로 전환된다."""
  room = models.CharField(max_length=160, unique=True, db_index=True)
  fan = models.ForeignKey(IntalkingUser, on_delete=models.SET_NULL,
    null=True, blank=True, related_name='+')
  infl = models.ForeignKey(IntalkingUser, on_delete=models.SET_NULL,
    null=True, blank=True, related_name='+')
  fan_track = models.FileField(upload_to=recording_path, null=True, blank=True)
  infl_track = models.FileField(upload_to=recording_path, null=True, blank=True)
  merged = models.FileField(upload_to=recording_path, null=True, blank=True)
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
