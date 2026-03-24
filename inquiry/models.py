from django.db import models
from django.utils import timezone
from datetime import timedelta
from account.models import IntalkingUser

class Inquiry(models.Model):
  STATUS_CHOICES = [
    ('UNANSWERED', '미답변'),
    ('ANSWERING', '답변중'),
    ('COMPLETED', '답변완료'),
  ]

  fan = models.ForeignKey(IntalkingUser, on_delete=models.CASCADE, related_name='inquiries')
  title = models.CharField(max_length=255)
  status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='UNANSWERED')
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ['-created_at']

  def __str__(self):
    return f'[{self.get_status_display()}] {self.title}'

  def check_completed(self):
    if self.status != 'ANSWERING':
      return
    
    last_admin = self.replies.filter(is_admin=True).order_by('-created_at').first()
    if not last_admin:
      return
    
    fan_after = self.replies.filter(is_admin=False, created_at__gt=last_admin.created_at).exists()
    if not fan_after and timezone.now() - last_admin.created_at > timedelta(hours=24):
      self.status = 'COMPLETED'
      self.save(update_fields=['status'])

  @classmethod
  def check_all_answering(cls):
    for inquiry in cls.objects.filter(status='ANSWERING'):
      inquiry.check_completed()


class InquiryReply(models.Model):
  inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name='replies')
  author = models.ForeignKey(IntalkingUser, on_delete=models.CASCADE, null=True, blank=True)
  is_admin = models.BooleanField(default=False)
  content = models.TextField()
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ['created_at']

  def __str__(self):
    role = '관리자' if self.is_admin else '팬'
    return f'[{role}] {self.content[:20]}'

  def save(self, *args, **kwargs):
    super().save(*args, **kwargs)
    if self.is_admin and self.inquiry.status == 'UNANSWERED':
      self.inquiry.status = 'ANSWERING'
      self.inquiry.save(update_fields=['status'])
    elif not self.is_admin and self.inquiry.status == 'ANSWERING':
      self.inquiry.status = 'ANSWERING'
      self.inquiry.save(update_fields=['status'])
