# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class Tenant(models.Model):
    name = models.CharField(max_length=100)
    subdomain = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Plano de assinatura
    PLAN_CHOICES = (
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    )
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    
    # Limites do plano
    max_users = models.IntegerField(default=5)
    max_meetings = models.IntegerField(default=10)
    max_duration = models.IntegerField(default=60)  # em minutos
    
    def __str__(self):
        return self.name

class User(AbstractUser):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='users', null=True)
    preferred_language = models.CharField(max_length=10, default='en')
    
    # Permissões específicas do tenant
    is_tenant_admin = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username