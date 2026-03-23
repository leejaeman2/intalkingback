from django.contrib import admin
from .models import Notice

@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
  list_display = ('type', 'author', 'title', 'created_at')
  list_filter = ('type',)
  search_fields = ('title', 'content')
  ordering = ('-created_at',)
  list_display_links = ('title',)
