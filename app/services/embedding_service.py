import logging
logger = logging.getLogger(__name__)

from openai import AsyncOpenAI
from typing import List
from app.core.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for a single text.
    Args:
        text (str): The input text to generate embedding for.
    Returns:
        List[float]: The generated embedding vector.
    """
    try:
        response = await client.embeddings.create(
            input=text,
            model=settings.EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding for text: {e}")
        raise

async def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts.
    Uses OpenAI's batch input (up to 2048 tokens per request) to minimize API calls.
    Args:
        texts (List[str]): A list of input texts to generate embeddings for.
    Returns:
        List[List[float]]: A list of embedding vectors corresponding to the input texts.
    """
    try:
        response = await client.embeddings.create(
            input=texts,
            model=settings.EMBEDDING_MODEL
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        logger.error(f"Error generating embeddings for texts: {e}")
        raise