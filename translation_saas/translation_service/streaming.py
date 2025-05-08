# translation_service/streaming.py
import asyncio
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .speech_to_text import SpeechToTextService
from .translation import TranslationService
from .text_to_speech import TextToSpeechService
from core.models import Meeting, Participant, TranscriptionSegment, TranslationSegment

class TranslationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket Consumer para streaming bidirecional de tradução.
    """
    
    async def connect(self):
        self.meeting_id = self.scope['url_route']['kwargs']['meeting_id']
        self.user = self.scope['user']
        
        # Verificar se o usuário tem acesso à reunião
        try:
            self.meeting = await self.get_meeting()
            self.participant = await self.get_or_create_participant()
        except Exception as e:
            await self.close(code=4000)
            return
        
        # Adicionar ao grupo da reunião
        self.room_group_name = f'meeting_{self.meeting_id}'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Inicializar serviços
        self.speech_service = SpeechToTextService()
        self.translation_service = TranslationService()
        self.speech_synthesis_service = TextToSpeechService()
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Remover do grupo da reunião
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Atualizar horário de saída do participante
        if hasattr(self, 'participant'):
            await self.update_participant_leave_time()
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Recebe dados do WebSocket
        """
        # Processar dados de áudio
        if bytes_data:
            await self.process_audio(bytes_data)
        
        # Processar mensagens de texto/controle
        elif text_data:
            try:
                data = json.loads(text_data)
                message_type = data.get('type')
                
                if message_type == 'config':
                    # Configuração de idiomas
                    speaking_language = data.get('speaking_language')
                    listening_language = data.get('listening_language')
                    
                    if speaking_language:
                        await self.update_speaking_language(speaking_language)
                    
                    if listening_language:
                        await self.update_listening_language(listening_language)
                
                elif message_type == 'start_meeting':
                    # Iniciar/ativar reunião
                    pass
                
                elif message_type == 'end_meeting':
                    # Finalizar reunião
                    await self.end_meeting()
            
            except json.JSONDecodeError:
                pass
    
    async def process_audio(self, audio_data):
        """
        Processa chunks de áudio recebidos
        """
        # Obter idioma do participante
        source_language = self.participant.speaking_language
        
        # Transcrever áudio
        transcription = await self.transcribe_audio(audio_data, source_language)
        
        if transcription:
            # Salvar transcrição
            transcription_segment = await self.save_transcription(transcription, source_language)
            
            # Enviar transcrição para todos os participantes
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'transcription_message',
                    'transcription': transcription,
                    'participant_id': self.participant.id,
                    'language': source_language
                }
            )
            
            # Traduzir para os idiomas de destino
            for target_language in self.meeting.target_languages:
                if target_language != source_language:
                    translation = await self.translate_text(transcription, source_language, target_language)
                    
                    if translation:
                        # Salvar tradução
                        await self.save_translation(transcription_segment, translation, target_language)
                        
                        # Sintetizar voz
                        audio = await self.synthesize_speech(translation, target_language)
                        
                        # Enviar tradução e áudio para participantes que ouvem nesse idioma
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                'type': 'translation_message',
                                'translation': translation,
                                'audio': audio,
                                'participant_id': self.participant.id,
                                'source_language': source_language,
                                'target_language': target_language
                            }
                        )
    
    async def transcribe_audio(self, audio_data, language_code):
        """
        Transcreve o áudio usando o serviço de reconhecimento de voz
        """
        # Esta é uma operação potencialmente bloqueante, então usamos run_in_executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            lambda: self.speech_service.transcribe_stream(audio_data, language_code)
        )
        return result
    
    async def translate_text(self, text, source_language, target_language):
        """
        Traduz o texto para o idioma alvo
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.translation_service.translate_text(text, target_language, source_language)
        )
        return result
    
    async def synthesize_speech(self, text, language_code):
        """
        Sintetiza o texto em voz
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.speech_synthesis_service.synthesize_speech(text, language_code)
        )
        return result
    
    # Métodos para enviar mensagens ao WebSocket
    async def transcription_message(self, event):
        """
        Enviar mensagem de transcrição para o WebSocket
        """
        # Enviar apenas se a mensagem for de interesse do participante
        if event['language'] == self.participant.listening_language:
            await self.send(text_data=json.dumps({
                'type': 'transcription',
                'text': event['transcription'],
                'participant_id': event['participant_id'],
                'language': event['language']
            }))
    
    async def translation_message(self, event):
        """
        Enviar mensagem de tradução para o WebSocket
        """
        # Enviar apenas se o idioma alvo for o que o participante está ouvindo
        if event['target_language'] == self.participant.listening_language:
            await self.send(text_data=json.dumps({
                'type': 'translation',
                'text': event['translation'],
                'participant_id': event['participant_id'],
                'source_language': event['source_language'],
                'target_language': event['target_language']
            }))
            
            # Enviar o áudio sintetizado
            if event.get('audio'):
                await self.send(bytes_data=event['audio'])
    
    # Métodos auxiliares para operações no banco de dados
    async def get_meeting(self):
        """
        Obtém a reunião pelo ID
        """
        from asgiref.sync import sync_to_async
        from django.shortcuts import get_object_or_404
        
        get_meeting = sync_to_async(get_object_or_404)
        return await get_meeting(Meeting, id=self.meeting_id, is_active=True)
    
    async def get_or_create_participant(self):
        """
        Obtém ou cria o participante para o usuário atual
        """
        from asgiref.sync import sync_to_async
        
        if self.user.is_authenticated:
            get_or_create = sync_to_async(Participant.objects.get_or_create)
            participant, created = await get_or_create(
                meeting=self.meeting,
                user=self.user,
                defaults={
                    'name': self.user.get_full_name() or self.user.username,
                    'email': self.user.email,
                    'speaking_language': self.user.preferred_language,
                    'listening_language': self.user.preferred_language
                }
            )
            return participant
        else:
            # Para usuários não autenticados, usar dados da sessão
            name = self.scope.get('session', {}).get('guest_name', 'Guest')
            email = self.scope.get('session', {}).get('guest_email')
            
            create = sync_to_async(Participant.objects.create)
            return await create(
                meeting=self.meeting,
                name=name,
                email=email,
                speaking_language='en',  # Padrão
                listening_language='en'  # Padrão
            )
    
    async def update_participant_leave_time(self):
        """
        Atualiza o horário de saída do participante
        """
        from asgiref.sync import sync_to_async
        from django.utils import timezone
        
        self.participant.leave_time = timezone.now()
        save = sync_to_async(self.participant.save)
        await save()
    
    async def update_speaking_language(self, language):
        """
        Atualiza o idioma de fala do participante
        """
        from asgiref.sync import sync_to_async
        
        self.participant.speaking_language = language
        save = sync_to_async(self.participant.save)
        await save()
    
    async def update_listening_language(self, language):
        """
        Atualiza o idioma de escuta do participante
        """
        from asgiref.sync import sync_to_async
        
        self.participant.listening_language = language
        save = sync_to_async(self.participant.save)
        await save()
    
    async def end_meeting(self):
        """
        Finaliza a reunião atual
        """
        from asgiref.sync import sync_to_async
        from django.utils import timezone
        
        self.meeting.is_active = False
        self.meeting.end_time = timezone.now()
        save = sync_to_async(self.meeting.save)
        await save()
        
        # Notificar todos os participantes
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'meeting_ended',
            }
        )
        
    async def meeting_ended(self, event):
        """
        Enviar notificação de que a reunião terminou
        """
        await self.send(text_data=json.dumps({
            'type': 'meeting_ended',
        }))
        
    async def save_transcription(self, text, language):
        """
        Salva um segmento de transcrição no banco de dados
        """
        from asgiref.sync import sync_to_async
        
        create = sync_to_async(TranscriptionSegment.objects.create)
        segment = await create(
            meeting=self.meeting,
            participant=self.participant,
            original_text=text,
            source_language=language
        )
        return segment
    
    async def save_translation(self, transcription_segment, translated_text, target_language):
        """
        Salva um segmento de tradução no banco de dados
        """
        from asgiref.sync import sync_to_async
        
        create = sync_to_async(TranslationSegment.objects.create)
        await create(
            transcription=transcription_segment,
            target_language=target_language,
            translated_text=translated_text
        )