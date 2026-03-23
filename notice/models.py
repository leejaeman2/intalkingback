from django.db import models

class Notice(models.Model):
  TYPE_CHOICES = [
    ('NOTICE', '공지사항'),
    ('FANMEETING', '팬미팅'),
    ('PARTY', '인파티'),
  ]

  author = models.CharField(max_length=255, default='관리자')
  type = models.CharField(max_length=10, choices=TYPE_CHOICES)
  title = models.CharField(max_length=255)
  content = models.TextField()
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ['-created_at']

  def __str__(self):
    return f'[{self.get_type_display()}] {self.title}'
