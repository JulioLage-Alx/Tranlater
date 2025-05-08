# translation_service/speech_to_text.py
import os
from google.cloud import speech
import io

class SpeechToTextService:
    def __init__(self):
        self.client = speech.SpeechClient()
    
    def transcribe_stream(self, audio_content, language_code='en-US', sample_rate=16000, streaming=True):
        """
        Transcrever áudio usando Google Speech-to-Text API.
        
        Args:
            audio_content: Conteúdo de áudio em bytes
            language_code: Código do idioma (ex: 'en-US', 'pt-BR')
            sample_rate: Taxa de amostragem do áudio em Hz
            streaming: Se True, usa streaming API, caso contrário usa reconhecimento síncrono
            
        Returns:
            Texto transcrito
        """
        if streaming:
            return self._transcribe_streaming(audio_content, language_code, sample_rate)
        else:
            return self._transcribe_sync(audio_content, language_code, sample_rate)
    
    def _transcribe_sync(self, audio_content, language_code, sample_rate):
        audio = speech.RecognitionAudio(content=audio_content)
        
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=sample_rate,
            language_code=language_code,
            enable_automatic_punctuation=True,
            use_enhanced=True,
            model="latest_short"  # Otimizado para diálogos curtos
        )
        
        response = self.client.recognize(config=config, audio=audio)
        
        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript
            
        return transcript
    
    def _transcribe_streaming(self, audio_generator, language_code, sample_rate):
        config = speech.StreamingRecognitionConfig(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,
                language_code=language_code,
                enable_automatic_punctuation=True,
                use_enhanced=True,
                model="latest_short"
            ),
            interim_results=True
        )
        
        def request_generator():
            yield speech.StreamingRecognizeRequest(streaming_config=config)
            for content in audio_generator:
                yield speech.StreamingRecognizeRequest(audio_content=content)
        
        responses = self.client.streaming_recognize(request_generator())
        
        for response in responses:
            for result in response.results:
                if result.is_final:
                    yield result.alternatives[0].transcript