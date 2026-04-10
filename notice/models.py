from django.db import models
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
  is_deleted = models.BooleanField(default=False)
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ['-created_at']

  def clean(self):
    if self.infl and self.type in ('FANMEETING', 'PARTY'):
      existing = Notice.objects.filter(
        infl=self.infl, type=self.type, is_deleted=False
      ).exclude(pk=self.pk)
      if existing.exists():
        type_name = self.get_type_display()
        raise ValidationError(f'{self.infl}에게 이미 진행 중인 {type_name}이(가) 있습니다.')

  def __str__(self):
    return f'[{self.get_type_display()}] {self.title}'
