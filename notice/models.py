from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from account.models import IntalkingUser

class Notice(models.Model):
  TYPE_CHOICES = [
    ('NOTICE', '공지사항'),
    ('FANMEETING', '팬미팅'),
    ('PARTY', '인파티'),
  ]

  infl = models.ForeignKey(IntalkingUser, on_delete=models.CASCADE, null=True, blank=True, related_name='notices')
  author = models.CharField(max_length=255, default='관리자')
  type = models.CharField(max_length=10, choices=TYPE_CHOICES)
  title = models.CharField(max_length=255)
  content = models.TextField()
  event_date = models.DateField(null=True, blank=True, verbose_name='진행일', help_text='팬미팅/인파티 진행일. 이 날짜가 지나면 앱에서 버튼이 사라집니다.')
  is_deleted = models.BooleanField(default=False)
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ['-created_at']

  @classmethod
  def active_events(cls, infl, type):
    # 삭제되지 않았고 진행일이 오늘 이후(또는 미지정)인 팬미팅/인파티
    return cls.objects.filter(infl=infl, type=type, is_deleted=False).filter(
      Q(event_date__isnull=True) | Q(event_date__gte=timezone.localdate()))

  @property
  def is_expired(self):
    return self.event_date is not None and self.event_date < timezone.localdate()

  def clean(self):
    if self.type in ('FANMEETING', 'PARTY') and not self.event_date:
      raise ValidationError({'event_date': '팬미팅/인파티는 진행일을 입력해야 합니다.'})
    if self.infl and self.type in ('FANMEETING', 'PARTY'):
      existing = Notice.active_events(self.infl, self.type).exclude(pk=self.pk)
      if existing.exists():
        type_name = self.get_type_display()
        raise ValidationError(f'{self.infl}에게 이미 진행 중인 {type_name}이(가) 있습니다.')

  def __str__(self):
    return f'[{self.get_type_display()}] {self.title}'

class NoticeApply(models.Model):
  notice = models.ForeignKey(Notice, on_delete=models.CASCADE, related_name='applies', verbose_name='공지')
  fan = models.ForeignKey(IntalkingUser, on_delete=models.CASCADE, related_name='notice_applies', verbose_name='신청자')
  created_at = models.DateTimeField(auto_now_add=True, verbose_name='신청일')

  class Meta:
    ordering = ['-created_at']
    unique_together = ('notice', 'fan')
    verbose_name = '팬미팅/인파티 신청'
    verbose_name_plural = '팬미팅/인파티 신청'

  def __str__(self):
    return f'{self.notice} - {self.fan}'
