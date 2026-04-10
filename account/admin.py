from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import IntalkingUser

@admin.register(IntalkingUser)
class IntalkingUserAdmin(UserAdmin):
    list_display = ('email', 'nickname', 'phone', 'fan', 'charnum', 'mbti', 'hobby', 'point', 'callmode', 'is_active')
    list_filter = ('fan', 'mbti', 'is_active')
    search_fields = ('email', 'nickname', 'phone')
    ordering = ('-date_joined',)
