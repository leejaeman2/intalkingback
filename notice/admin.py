from django.contrib import admin
from .models import Notice, NoticeApply
from account.models import IntalkingUser

class NoticeApplyInline(admin.TabularInline):
  model = NoticeApply
  extra = 0
  can_delete = False
  fields = ('fan', 'fan_nickname', 'fan_phone', 'created_at')
  readonly_fields = fields
  verbose_name_plural = '신청자 목록'

  def has_add_permission(self, request, obj=None):
    return False

  @admin.display(description='닉네임')
  def fan_nickname(self, obj):
    return obj.fan.nickname

  @admin.display(description='전화번호')
  def fan_phone(self, obj):
    return obj.fan.phone

@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
  list_display = ('type', 'author', 'title', 'event_date', 'apply_count', 'is_deleted', 'created_at')
  list_filter = ('type', 'is_deleted')
  search_fields = ('title', 'content')
  ordering = ('-created_at',)
  list_display_links = ('title',)
  readonly_fields = ('author',)
  fields = ('type', 'infl', 'author', 'title', 'event_date', 'content', 'is_deleted')
  inlines = (NoticeApplyInline,)

  @admin.display(description='신청자 수')
  def apply_count(self, obj):
    return obj.applies.count() if obj.type in ('FANMEETING', 'PARTY') else '-'

  def formfield_for_foreignkey(self, db_field, request, **kwargs):
    if db_field.name == 'infl':
      kwargs['queryset'] = IntalkingUser.objects.filter(fan='INFL')
    return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(NoticeApply)
class NoticeApplyAdmin(admin.ModelAdmin):
  list_display = ('notice', 'notice_type', 'notice_infl', 'fan', 'fan_nickname', 'fan_phone', 'created_at')
  list_filter = ('notice__type', 'notice')
  search_fields = ('notice__title', 'fan__email', 'fan__nickname', 'fan__phone')
  ordering = ('-created_at',)
  list_select_related = ('notice', 'notice__infl', 'fan')

  def has_add_permission(self, request):
    return False

  def has_change_permission(self, request, obj=None):
    return False

  @admin.display(description='구분')
  def notice_type(self, obj):
    return obj.notice.get_type_display()

  @admin.display(description='인플루언서')
  def notice_infl(self, obj):
    return obj.notice.infl

  @admin.display(description='닉네임')
  def fan_nickname(self, obj):
    return obj.fan.nickname

  @admin.display(description='전화번호')
  def fan_phone(self, obj):
    return obj.fan.phone
