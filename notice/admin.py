from django.contrib import admin
from .models import Notice
from account.models import IntalkingUser

@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
  list_display = ('type', 'author', 'title', 'is_deleted', 'created_at')
  list_filter = ('type', 'is_deleted')
  search_fields = ('title', 'content')
  ordering = ('-created_at',)
  list_display_links = ('title',)

  def formfield_for_foreignkey(self, db_field, request, **kwargs):
    if db_field.name == 'infl':
      kwargs['queryset'] = IntalkingUser.objects.filter(fan='INFL')
    return super().formfield_for_foreignkey(db_field, request, **kwargs)
