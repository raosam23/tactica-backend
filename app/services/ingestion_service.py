from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.services import (chunk_documents, generate_embeddings_batch,
                          scrape_rss_feeds, scrape_wikipedia_articles)


async def run_ingestion(
    session: AsyncSession,
    wiki_titles: List[str],
    rss_urls: List[str],
    sport: Optional[str] = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> Dict[str, int]:
    """
    Run the full ingestion pipline: scrape -> chunk -> embed -> store
    Args:
        session (AsyncSession): The database session to use for storing documents
        wiki_titles (List[str]): A list of Wikipedia article titles to scrape
        rss_urls (List[str]): A list of RSS feed URLs to scrape
        sport (Optional[str]): An optional sport category to tag all articles with
        chunk_size (int): The maximum characters per chunk
        chunk_overlap (int): The number of overlapping characters between chunks
    """
    # --- Step 1: Scraping contents from Wikipedia and RSS feeds ---
    wiki_docs = await scrape_wikipedia_articles(wiki_titles, sport)
    rss_docs = scrape_rss_feeds(rss_urls, sport)

    all_docs = wiki_docs + rss_docs

    # --- Step 2: Chunking documents while preserving metadata ---
    chunks = chunk_documents(all_docs, chunk_size, chunk_overlap)

    # --- Step 3: Embedding chunks ---
    texts = [chunk["content"] for chunk in chunks]
    # embeddings = await generate_embeddings_batch(texts)
    all_embeddings = []
    for idx in range(0, len(texts), 2048):
        batch = texts[idx: idx + 2048]
        batch_result = await generate_embeddings_batch(batch)
        all_embeddings.extend(batch_result)

    # --- Step 4: Attach embeddings to chunks ---
    for idx, chunk in enumerate(chunks):
        chunk["embedding"] = all_embeddings[idx]

    # --- Step 5: Store in database ---
    for chunk in chunks:
        document = Document(
            content=chunk["content"],
            embedding=chunk["embedding"],
            source=chunk["source"],
            sport=chunk.get("sport", None),
            tags=chunk.get("tags", []),
            metadata_=chunk.get("metadata_", {}),
        )
        session.add(document)
    await session.commit()

    # --- Step 6: Return stats
    return {
        "scrapped": len(all_docs),
        "chunks": len(chunks),
        "embeddings": len(all_embeddings),
        "stored": len(chunks),
    }