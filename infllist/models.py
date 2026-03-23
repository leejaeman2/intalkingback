from django.db import models
from account.models import IntalkingUser

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
