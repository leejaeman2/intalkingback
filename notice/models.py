from django.db import models
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

  def __str__(self):
    return f'[{self.get_type_display()}] {self.title}'
