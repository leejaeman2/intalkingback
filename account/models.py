from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.
class IntalkingUser(AbstractUser):
  FAN_CHOICES = [
    ('FAN', '팬'),
    ('INFL', '인플')
  ]

  MBTI_CHOICES = [
    ('ISTJ', 'ISTJ'), ('ISFJ', 'ISFJ'), ('INFJ', 'INFJ'), ('INTJ', 'INTJ'),
    ('ISTP', 'ISTP'), ('ISFP', 'ISFP'), ('INFP', 'INFP'), ('INTP', 'INTP'),
    ('ESTP', 'ESTP'), ('ESFP', 'ESFP'), ('ENFP', 'ENFP'), ('ENTP', 'ENTP'),
    ('ESTJ', 'ESTJ'), ('ESFJ', 'ESFJ'), ('ENFJ', 'ENFJ'), ('ENTJ', 'ENTJ'),
  ]

  username = models.CharField(max_length=255)
  email = models.EmailField(max_length=255, unique=True)
  nickname = models.CharField(max_length=255, unique=True, null=True, blank=True)
  phone = models.CharField(max_length=20, unique=True)
  fan = models.CharField(max_length=4, choices=FAN_CHOICES)
  bank = models.CharField(max_length=255, null=True, blank=True)
  account = models.CharField(max_length=255, null=True, blank=True)
  code = models.CharField(max_length=255, unique=True, null=True, blank=True)
  charnum = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(33)], null=True, blank=True)
  hobby = models.CharField(max_length=255, null=True, blank=True)
  food = models.CharField(max_length=255, null=True, blank=True)
  mbti = models.CharField(max_length=4, choices=MBTI_CHOICES, null=True, blank=True)
  info = models.TextField(null=True, blank=True)
  point = models.IntegerField(default=0)
  callmode = models.BooleanField(default=True)
  photo1 = models.ImageField(upload_to='profile/')
  photo2 = models.ImageField(upload_to='profile/', null=True, blank=True)
  photo3 = models.ImageField(upload_to='profile/', null=True, blank=True)
  photo4 = models.ImageField(upload_to='profile/', null=True, blank=True)
  photo5 = models.ImageField(upload_to='profile/', null=True, blank=True)
  photo6 = models.ImageField(upload_to='profile/', null=True, blank=True)
  photo7 = models.ImageField(upload_to='profile/', null=True, blank=True)
  photo8 = models.ImageField(upload_to='profile/', null=True, blank=True)

  USERNAME_FIELD = 'email'
  REQUIRED_FIELDS = ['username']

  def __str__(self):
    return f'{self.email} ({self.nickname})' if self.nickname else self.email


class DeletedUser(models.Model):
  email = models.EmailField(max_length=255)
  nickname = models.CharField(max_length=255, null=True, blank=True)
  phone = models.CharField(max_length=20)
  fan = models.CharField(max_length=4)
  point = models.IntegerField(default=0)
  deleted_at = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return self.email
