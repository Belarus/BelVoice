import asyncio
import os
import wave
from typing import Optional

from google import genai
from google.genai import types
from google.genai.types import LanguageHints

from belvoice.asr.SplitData import VoiceFile, VoicePart


class STTGeminiLive:
    """
    Транскрыпцыя аўдыяфайла праз Gemini Live API (рэжым рэальнага часу), выкарыстоўваючы
    афіцыйную бібліятэку google-genai напрамую (без litellm).

    gemini-3.5-transcribe-live: максімальная даўжыня - 10 хвілін.
    Manual VAD (Push-to-Talk) працуе так: ён вяртае generation_complete=True
    калі перадалі audio_stream_end=True, але такім чынам можна даслаць недзе не больш за 3 хвіліны аўдыя,
    пасля чаго мадэль вяртае generation_complete=True незалежна ад audio_stream_end.
    Калі выключыць Manual VAD, мадэль будзе дасылаць generation_complete=True на паўзах, і трэба чакаць заканчэння па timeout.

    gemini-3.5-live-translate-preview: яе таксама можна было б выкарыстоўваць для транскрыпта,
    але мадэль мае некалькі істотных мінусаў:
     - якасць распазнавання горшая за gemini-3.5-transcribe-live,
     - перадае часам  interrupted=True
     - не ўлічвае audio_stream_end=True, то бок трэба неяк выкручвацца для дэтэкта канца аўдыя
     - перадае аўдыя ў адказ, што павялічвае трафік
    З улікам гэтых недахопаў і таго, што яе кошт і бясплатныя ліміты не большыя за gemini-3.5-transcribe-live, яе не варта выкарыстоўваць.
    """

    CHUNK_FRAMES = 1600  # колькі "фрэймаў" WAV-файла адпраўляць у адным пакеце
    CHUNK_DELAY = 0.1
    RESPONSE_TIMEOUT = 10.0  # секунд чакання наступнага паведамлення / generation_complete пасля адпраўкі аўдыя
    SILENCE_DURATION_AFTER_S = 2.0  # секунд маўчання пасля аўдыя

    def __init__(self,
                 model_name: str = "gemini-3.5-transcribe-live",
                 audio_transcription_config: Optional[types.AudioTranscriptionConfig] = None) -> None:
        self._api_key = os.environ.get("GEMINI_API_KEY")
        if not self._api_key:
            raise Exception("Памылка: не ўстаноўлены GEMINI_API_KEY у якасці зменнай асяроддзя.")

        self._model_name = model_name
        self._client = genai.Client(api_key=self._api_key)

        if audio_transcription_config:
            self._audio_transcription_config = audio_transcription_config
        else:
            self._audio_transcription_config = types.AudioTranscriptionConfig(
                language_hints=LanguageHints(language_codes=["be"]))

        self._realtime_input_config = types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(disabled=True),
        )

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
            input_audio_transcription=self._audio_transcription_config,
            realtime_input_config=self._realtime_input_config
        )

        transcript_parts: list[str] = []
        loop = asyncio.get_event_loop()
        generation_completed = False

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
                            raise TimeoutError(
                                f"Таймаут ({self.RESPONSE_TIMEOUT} с): сервер не вярнуў generation_complete=True пасля адпраўкі аўдыя."
                            )

                        try:
                            response = await asyncio.wait_for(receiver.__anext__(), timeout=remaining)
                        except StopAsyncIteration:
                            raise RuntimeError(
                                "Злучэнне закрылася датэрмінова да атрымання generation_complete=True."
                            )
                        except asyncio.TimeoutError:
                            raise TimeoutError(
                                f"Таймаут ({self.RESPONSE_TIMEOUT} с): сервер не вярнуў generation_complete=True пасля адпраўкі аўдыя."
                            )
                    else:
                        # адпраўка яшчэ не завершана - чакаем наступнае паведамленне без таймауту
                        try:
                            response = await receiver.__anext__()
                        except StopAsyncIteration:
                            raise RuntimeError(
                                "Злучэнне закрылася датэрмінова падчас адпраўкі аўдыя (не атрымана generation_complete=True)."
                            )

                    server_content = response.server_content
                    if server_content is None:
                        continue

                    input_transcription = server_content.input_transcription
                    if input_transcription and input_transcription.text:
                        transcript_parts.append(input_transcription.text)
                        last_useful_ts = loop.time()

                    if server_content.generation_complete:
                        generation_completed = True
                        break

                    if (
                            server_content.turn_complete
                            or server_content.turn_complete_reason is not None
                            or server_content.waiting_for_input
                    ):
                        raise RuntimeError(f"Нечаканы server_content: {server_content}")

                if not generation_completed:
                    raise RuntimeError("Транскрыпцыя завершана без атрымання generation_complete=True.")
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
            sample_width = wav_file.getsampwidth()
            n_channels = wav_file.getnchannels()
            while True:
                chunk = wav_file.readframes(self.CHUNK_FRAMES)
                if not chunk:
                    break
                await session.send_realtime_input(
                    audio=types.Blob(data=chunk, mime_type=f"audio/pcm;rate={sample_rate}")
                )
                await asyncio.sleep(self.CHUNK_DELAY)

        # дадаём ~2 сек цішыні, каб мадэль паспела дапрацаваць апошняе слова
        silence_frames = int(sample_rate * self.SILENCE_DURATION_AFTER_S)
        silence_chunk = b"\x00" * (silence_frames * sample_width * n_channels)
        await session.send_realtime_input(
            audio=types.Blob(data=silence_chunk, mime_type=f"audio/pcm;rate={sample_rate}")
        )
        await asyncio.sleep(0.3)

        await session.send_realtime_input(activity_end=types.ActivityEnd())
        await asyncio.sleep(0.3)  # дадатковая паўза перад канчатковым сігналам
        await session.send_realtime_input(audio_stream_end=True)
