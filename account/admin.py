from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from .models import IntalkingUser, InflCode

@admin.register(IntalkingUser)
class IntalkingUserAdmin(UserAdmin):
    list_display = ('email', 'nickname', 'phone', 'fan', 'charnum', 'mbti', 'hobby', 'point', 'callmode', 'is_active')
    list_filter = ('fan', 'mbti', 'is_active')
    search_fields = ('email', 'nickname', 'phone')
    ordering = ('-date_joined',)


@admin.register(InflCode)
class InflCodeAdmin(admin.ModelAdmin):
    change_list_template = 'admin/account/inflcode/change_list.html'
    list_display = ('code', 'memo', 'is_used', 'used_at', 'created_at')
    list_filter = ('is_used',)
    search_fields = ('code', 'memo')
    ordering = ('-created_at',)

    def get_fields(self, request, obj=None):
        if obj is None:
            return ('memo',)
        return ('code', 'memo', 'is_used', 'used_at', 'created_at')

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        return ('code', 'used_at', 'created_at')

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('generate/', self.admin_site.admin_view(self.generate_view), name='account_inflcode_generate'),
        ]
        return custom + urls

    def generate_view(self, request):
        try:
            count = int(request.POST.get('count', 1)) if request.method == 'POST' else 1
        except (TypeError, ValueError):
            count = 1
        count = max(1, min(count, 100))
        for _ in range(count):
            InflCode.objects.create()
        messages.success(request, f'{count}개의 코드가 생성되었습니다.')
        return HttpResponseRedirect(reverse('admin:account_inflcode_changelist'))
