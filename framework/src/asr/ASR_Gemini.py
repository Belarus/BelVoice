from litellm import completion, create_file
from litellm.files.main import file_delete


class ASR_Gemini:
    """
    See models list on the https://models.litellm.ai/
    Usually, you need to set LLM's token into some env variable.
    Выкарыстоўвайце толькі назвы мадэляў, якія пачынаюцца з 'gemini/'. Напрыклад, 'gemini/gemini-3-flash-preview'.
    """

    def __init__(self, model_name: str):
        self._model_name = model_name

    PROMPT = """
    Genarate a transcript of this Belarusian language audio. Avoid any preambles.
    """

    def transcript(self, audio_file_path: str) -> str:
        if not audio_file_path.endswith(".flac"):
            raise Exception(f"{audio_file_path} is not a flac file")
        # upload file
        audio_file = create_file(file=audio_file_path, custom_llm_provider="gemini", purpose="user_data")

        response = completion(
            model=self._model_name,
            messages=[{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": self.PROMPT
                }, {
                    "type": "file",
                    "file": {"file_id": audio_file.id, "format": "audio/flac"}
                }]
            }],
            temperature=0.0
        )

        # delete file
        file_delete(audio_file.id, custom_llm_provider="gemini")

        return response.choices[0].message.content
