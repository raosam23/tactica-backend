from autogen_ext.models.openai import OpenAIChatCompletionClient

from app.core.config import settings


def create_model_client() -> OpenAIChatCompletionClient:
    return OpenAIChatCompletionClient(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
    )