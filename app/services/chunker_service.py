from typing import Any, Dict, List


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Splits a single text into overlapping chunks
    Args:
        text (str): The text to split
        chunk_size (int): The maximum characters per chunk
        overlap (int): The number of overlapping characters between chunks
    Returns:
        List[str]: A list of chunks
    """
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be > 0 and overlap must be >= 0 and < chunk_size")
    
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def chunk_documents(documents: List[dict], chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Chunk multiple documents' content while preserving metadata

    Args:
        documents (List[dict]): A list of dicts from scrapper (with title, content, url, source, sport, tags)
        chunk_size (int): The maximum characters per chunk
        chunk_overlap (int): The number of overlapping characters between chunks
    Returns:
        List[Dict[str, Any]]: A list of chunk dicts, each with chunked content + original metadata
    """
    all_chunks = []
    for doc in documents:
        text_chunks = chunk_text(doc["content"], chunk_size, chunk_overlap)
        for chunk in text_chunks:
            all_chunks.append({
                "content": chunk,
                "source": doc["source"],
                "sport": doc.get("sport", None),
                "tags": doc.get("tags", []),
                "metadata_": {
                    "title": doc.get("title", ""),
                    "url": doc.get("url", ""),
                }
            })
    return all_chunks