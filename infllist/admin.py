from django.contrib import admin
from django.utils.html import format_html
from .models import InflList, CallRecording

@admin.register(InflList)
class InflListAdmin(admin.ModelAdmin):
    list_display = ('fan', 'infl', 'duration', 'last', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('fan__email', 'infl__email')
    ordering = ('-created_at',)

@admin.register(CallRecording)
class CallRecordingAdmin(admin.ModelAdmin):
    list_display = ('room', 'fan', 'infl', 'duration', 'player', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('room', 'fan__email', 'infl__email')
    ordering = ('-created_at',)
    readonly_fields = ('player',)

    @admin.display(description='녹음')
    def player(self, obj):
        if not obj.merged:
            return '-'
        # S3 비공개 버킷 → 1시간짜리 서명 URL
        url = obj.merged.url
        return format_html(
            '<audio controls preload="none" src="{}"></audio> <a href="{}" download>다운로드</a>', url, url)
