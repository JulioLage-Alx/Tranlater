# core/models.py
from django.db import models
from accounts.models import User, Tenant

class Meeting(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='meetings')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_meetings')
    name = models.CharField(max_length=200)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Configurações
    source_language = models.CharField(max_length=10, default='en')
    target_languages = models.JSONField(default=list)  # Lista de idiomas alvo
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Participant(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)  # Para participantes não registrados
    email = models.EmailField(null=True, blank=True)
    join_time = models.DateTimeField(auto_now_add=True)
    leave_time = models.DateTimeField(null=True, blank=True)
    
    # Configurações de idioma
    speaking_language = models.CharField(max_length=10, default='en')
    listening_language = models.CharField(max_length=10, default='en')
    
    def __str__(self):
        return self.name or self.user.username if self.user else "Anonymous"

class TranscriptionSegment(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='transcriptions')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='transcriptions')
    original_text = models.TextField()
    source_language = models.CharField(max_length=10)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.participant} - {self.timestamp}"

class TranslationSegment(models.Model):
    transcription = models.ForeignKey(TranscriptionSegment, on_delete=models.CASCADE, related_name='translations')
    target_language = models.CharField(max_length=10)
    translated_text = models.TextField()
    
    def __str__(self):
        return f"{self.transcription.participant} - {self.target_language}"