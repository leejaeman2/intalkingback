from django.contrib import admin
from .models import InflList, CallRecording

@admin.register(InflList)
class InflListAdmin(admin.ModelAdmin):
    list_display = ('fan', 'infl', 'duration', 'last', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('fan__email', 'infl__email')
    ordering = ('-created_at',)

@admin.register(CallRecording)
class CallRecordingAdmin(admin.ModelAdmin):
    list_display = ('room', 'fan', 'infl', 'duration', 'merged', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('room', 'fan__email', 'infl__email')
    ordering = ('-created_at',)
