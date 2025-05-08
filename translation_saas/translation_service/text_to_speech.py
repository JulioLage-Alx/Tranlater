# translation_service/text_to_speech.py
import boto3
import io

class TextToSpeechService:
    def __init__(self, region_name=None):
        self.client = boto3.client('polly', region_name=region_name)
    
    def synthesize_speech(self, text, language_code='en-US', voice_id=None, output_format='mp3', streaming=True):
        """
        Sintetizar voz usando Amazon Polly.
        
        Args:
            text: Texto a ser sintetizado
            language_code: Código do idioma (ex: 'en-US', 'pt-BR')
            voice_id: ID da voz (opcional, será escolhido pelo idioma se não especificado)
            output_format: Formato de saída ('mp3' ou 'pcm')
            streaming: Se True, usa streaming API
            
        Returns:
            Áudio sintetizado como bytes
        """
        if not text:
            return None
            
        # Selecionar voz adequada para o idioma se não especificada
        if not voice_id:
            voice_id = self._get_voice_for_language(language_code)
        
        # Definir formato de saída
        output_format = 'mp3' if output_format.lower() == 'mp3' else 'pcm'
        
        if streaming:
            return self._synthesize_streaming(text, voice_id, output_format)
        else:
            return self._synthesize_standard(text, voice_id, output_format)
    
    def _synthesize_standard(self, text, voice_id, output_format):
        response = self.client.synthesize_speech(
            Text=text,
            OutputFormat=output_format,
            VoiceId=voice_id,
            Engine='neural'  # Usar modelo neural para melhor qualidade
        )
        
        return response['AudioStream'].read()
    
    def _synthesize_streaming(self, text, voice_id, output_format):
        response = self.client.synthesize_speech(
            Text=text,
            OutputFormat=output_format,
            VoiceId=voice_id,
            Engine='neural'
        )
        
        # Para streaming, retornamos o stream diretamente
        return response['AudioStream']
    
    def _get_voice_for_language(self, language_code):
        """
        Mapeia o código de idioma para uma voz neural do Polly.
        """
        language_voice_map = {
            'en-US': 'Matthew',
            'en-GB': 'Amy',
            'pt-BR': 'Camila',
            'es-ES': 'Lucia',
            'fr-FR': 'Lea',
            'de-DE': 'Vicki',
            'it-IT': 'Bianca',
            'ja-JP': 'Takumi',
            'ko-KR': 'Seoyeon',
            'zh-CN': 'Zhiyu',
        }
        
        # Extrair código de idioma principal se necessário
        main_lang = language_code.split('-')[0]
        
        # Tentar obter voz exata, depois tentar pelo idioma principal
        return language_voice_map.get(language_code, 
               language_voice_map.get(f"{main_lang}-{main_lang.upper()}", 'Matthew'))