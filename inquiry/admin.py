from django.contrib import admin
from .models import Inquiry, InquiryReply

@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
  list_display = ('fan', 'title', 'status', 'created_at')
  list_filter = ('status',)
  search_fields = ('title', 'fan__email')
  ordering = ('-created_at',)
  list_display_links = ('title',)

@admin.register(InquiryReply)
class InquiryReplyAdmin(admin.ModelAdmin):
  list_display = ('inquiry', 'is_admin', 'content', 'created_at')
  list_filter = ('is_admin',)
  search_fields = ('content',)
  ordering = ('-created_at',)
