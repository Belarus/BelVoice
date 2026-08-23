import asyncio
import os
import wave

from google import genai
from google.genai import types
from google.genai.types import LanguageHints

from belvoice.asr.SplitData import VoiceFile, VoicePart


class STTGeminiLive:
    """
    Транскрыпцыя аўдыяфайла праз Gemini Live API (рэжым рэальнага часу), выкарыстоўваючы
    афіцыйную бібліятэку google-genai напрамую (без litellm).

    Патрабуецца ўсталяваць бібліятэку: pip install google-genai

    Мадэль па змаўчанні - "gemini-3.5-live-translate-preview". Нягледзячы на назву мадэлі
    (яна прызначана таксама і для перакладу), тут выкарыстоўваецца толькі яе ўбудаваная
    функцыя транскрыпцыі ўваходнага аўдыя (input_audio_transcription), таму НІЯКАГА
    перакладу ці генерацыі адказу мадэллю не адбываецца - мова транскрыпту застаецца
    такой жа, як і мова зыходнага аўдыя (беларуская).
    """

    MODEL_NAME = "gemini-3.5-live-translate-preview"

    CHUNK_FRAMES = 1600  # колькі "фрэймаў" WAV-файла адпраўляць у адным пакеце
    CHUNK_DELAY = 0.1
    RESPONSE_TIMEOUT = 5.0  # секунд чакання наступнага паведамлення, пасля чаго лічым, што сервер больш нічога не дашле

    PROMPT = "Аўдыя на беларускай мове. Транскрыбуй толькі гэты тэкст, без перакладу. Выкарыстоўвай ТОЛЬКІ беларускую мову."

    def __init__(self, model_name: str = None, prompt: str = PROMPT) -> None:
        self._api_key = os.environ.get("GEMINI_API_KEY")
        if not self._api_key:
            raise Exception("Памылка: не ўстаноўлены GEMINI_API_KEY у якасці зменнай асяроддзя.")

        self._model_name = model_name or self.MODEL_NAME
        self._client = genai.Client(api_key=self._api_key)
        self._prompt = prompt

    def transcript_file(self, audio_file_path: str, convert_to_format: str = "wav") -> str:
        """
        Робіць транскрыпт усяго файла праз Gemini Live API (без разбіўкі на сегменты).
        Аўдыя заўсёды спачатку канвертуецца ў WAV/PCM 16kHz mono, бо гэтага патрабуе Live API.
        """
        temp_file = VoiceFile.extract_wav(audio_file_path, convert_to_format=convert_to_format or "wav")
        try:
            return asyncio.run(self._transcript_file_async(temp_file))
        finally:
            os.remove(temp_file)

    def transcript_parts(self, data: VoiceFile) -> None:
        """
        Робіць транскрыпт для кожнага сегмента, але без унутраных таймстэмпаў і пераразбіўкі сегментаў.
        """
        for segment in data.segments:
            if segment.text:
                continue
            self.transcript_part(data, segment)

    def transcript_part(self, data: VoiceFile, segment: VoicePart) -> None:
        """
        Робіць транскрыпт для аднаго сегмента.
        """
        temp_file = data.segment2wav(segment)
        try:
            segment.text = asyncio.run(self._transcript_file_async(temp_file))
        finally:
            os.remove(temp_file)

    async def _transcript_file_async(self, wav_file_path: str) -> str:
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.TEXT],
            input_audio_transcription=types.AudioTranscriptionConfig(language_hints=LanguageHints(language_codes=["be"])),
            system_instruction=types.Content(
                parts=[types.Part(text=self._prompt)]
            ),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(disabled=True),
            )
        )

        transcript_parts: list[str] = []
        loop = asyncio.get_event_loop()

        async with self._client.aio.live.connect(model=self._model_name, config=config) as session:
            # запускаем адпраўку файла як асобную задачу, каб прыём адказаў ад сервера
            # мог стартаваць адразу, не чакаючы поўнай перадачы аўдыя
            send_task = asyncio.create_task(self._send_audio_file(session, wav_file_path))

            try:
                receiver = session.receive()
                # таймаут неактыўнасці правяраецца толькі пасля таго, як увесь файл ужо
                # цалкам адпраўлены (send_task завершана) - да гэтага моманту чакаем
                # адказы сервера без абмежавання па часе
                last_useful_ts = None
                sending_finished = False

                while True:
                    if send_task.done():
                        if not sending_finished:
                            # файл толькі што дасланы цалкам - пачынаем адлік таймауту з гэтага моманту,
                            # незалежна ад таго, калі прыходзілі папярэднія паведамленні
                            sending_finished = True
                            last_useful_ts = loop.time()

                        remaining = self.RESPONSE_TIMEOUT - (loop.time() - last_useful_ts)
                        if remaining <= 0:
                            # даўно не было нічога карыснага - лічым транскрыпцыю завершанай
                            break

                        try:
                            response = await asyncio.wait_for(receiver.__anext__(), timeout=remaining)
                        except StopAsyncIteration:
                            break
                        except asyncio.TimeoutError:
                            break
                    else:
                        # адпраўка яшчэ не завершана - чакаем наступнае паведамленне без таймауту
                        try:
                            response = await receiver.__anext__()
                        except StopAsyncIteration:
                            break

                    server_content = response.server_content
                    if server_content is None:
                        continue

                    input_transcription = server_content.input_transcription
                    if input_transcription and input_transcription.text:
                        transcript_parts.append(input_transcription.text)
                        print(input_transcription)
                        last_useful_ts = loop.time()

                    if (
                            server_content.turn_complete
                            or server_content.generation_complete
                            or server_content.turn_complete_reason is not None
                            or server_content.waiting_for_input
                    ):
                        break
                    # усе іншыя паведамленні (напр. model_turn з audio-цішынёй) НЕ скідаюць таймаут
            finally:
                # калі прыём завяршыўся раней, чым адпраўка (напр. з-за таймаута),
                # усё роўна дачакаемся/скасуем задачу адпраўкі і пракінем яе памылкі, калі яны былі
                if not send_task.done():
                    send_task.cancel()
                try:
                    await send_task
                except asyncio.CancelledError:
                    pass

        return "".join(transcript_parts).strip()

    async def _send_audio_file(self, session, file_path: str) -> None:
        await session.send_realtime_input(activity_start=types.ActivityStart())
        with wave.open(file_path, 'rb') as wav_file:
            sample_rate = wav_file.getframerate()
            while True:
                chunk = wav_file.readframes(self.CHUNK_FRAMES)
                if not chunk:
                    break
                await session.send_realtime_input(
                    audio=types.Blob(data=chunk, mime_type=f"audio/pcm;rate={sample_rate}")
                )
                await asyncio.sleep(self.CHUNK_DELAY)  # невялікая паўза, каб імітаваць стрымінг у рэальным часе

        await session.send_realtime_input(activity_end=types.ActivityEnd())
        await session.send_realtime_input(audio_stream_end=True)
        print("=============== file sent =====")

