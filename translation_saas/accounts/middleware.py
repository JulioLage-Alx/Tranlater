# accounts/middleware.py
from django.conf import settings
from .models import Tenant

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extrair o subdomínio da solicitação
        host = request.get_host().split(':')[0]
        subdomain = host.split('.')[0] if '.' in host else None
        
        # Definir o tenant atual
        request.tenant = None
        if subdomain and subdomain != 'www':
            try:
                request.tenant = Tenant.objects.get(subdomain=subdomain, is_active=True)
            except Tenant.DoesNotExist:
                pass
        
        response = self.get_response(request)
        return response