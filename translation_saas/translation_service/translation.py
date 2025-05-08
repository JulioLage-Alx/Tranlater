# translation_service/translation.py
from google.cloud import translate_v2 as translate

class TranslationService:
    def __init__(self):
        self.client = translate.Client()
    
    def translate_text(self, text, target_language, source_language=None):
        """
        Traduzir texto usando Google Translate API.
        
        Args:
            text: Texto a ser traduzido
            target_language: Código do idioma de destino (ex: 'en', 'pt')
            source_language: Código do idioma de origem (opcional)
            
        Returns:
            Texto traduzido
        """
        if not text:
            return ""
            
        result = self.client.translate(
            text,
            target_language=target_language,
            source_language=source_language,
            format_="text"
        )
        
        return result['translatedText']
    
    def detect_language(self, text):
        """
        Detectar idioma do texto.
        
        Args:
            text: Texto para detecção de idioma
            
        Returns:
            Código do idioma detectado
        """
        if not text:
            return "en"
            
        result = self.client.detect_language(text)
        
        # Resultado vem como lista se o texto for lista
        if isinstance(result, list):
            return result[0]['language']
        return result['language']