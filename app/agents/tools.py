import uuid
from typing import Callable, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ingestion_service import run_ingestion
from app.services.rag_service import (AddConversationMemoryService,
                                      SearchConversationMemoryService,
                                      SearchDocumentsService)


def make_tools(session: AsyncSession, conversation_id: uuid.UUID, sport: Optional[str] = None) -> Tuple[Dict[str, Callable[..., str]], List]:
    cited_documents = []
    async def search_stats(query: str) -> str:
        """Find factual sports statistics for a specific query.

        Use this tool when the response needs precise factual data such as
        player stats, team stats, match records, rankings, totals, averages,
        win-loss numbers, or other numeric evidence.

        Args:
            query: A focused search query describing the statistic, player,
                team, match, season, or record to look up.

        Returns:
            A numbered plain-text list of relevant statistical snippets and
            their sources, or a fallback message when nothing relevant is found.
        """
        search_results = await SearchDocumentsService(session, query, sport=sport, limit=5)
        if not search_results:
            return "No relevant stats found."
        response = "Here are some stats that might be relevant:\n"
        for idx, (doc, score) in enumerate(search_results, start=1):
            response += f"{idx}. {doc.content} (Source: {doc.source})\n"
            cited_documents.append((doc.id, score))
        return response

    async def search_articles(query: str) -> str:
        """Find narrative sports content for background, history, or context.

        Use this tool when the response needs article-style material such as
        stories, historical background, event summaries, career arcs, or broad
        contextual information rather than narrowly focused statistics.

        Args:
            query: A search query describing the topic, event, player, team,
                or storyline that needs richer narrative context.

        Returns:
            A numbered plain-text list of relevant article-style snippets and
            their sources, or a fallback message when nothing relevant is found.
        """
        search_results = await SearchDocumentsService(session, query, sport=sport, limit=5)
        if not search_results:
            return "No relevant articles found."
        response = "Here are some articles that might be relevant:\n"
        for idx, (doc, score) in enumerate(search_results, start=1):
            response += f"{idx}. {doc.content} (Source: {doc.source})\n"
            cited_documents.append((doc.id, score))
        return response

    async def compare_players(players: List[str]) -> str:
        """Compare two or more players using retrieved evidence from the knowledge base.

        Use this tool when the user asks to compare players across performance,
        achievements, style, record, impact, or reputation. This tool searches
        for each player individually and returns grouped evidence for side-by-side
        comparison.

        Args:
            players: A list of player names that should be compared using
                retrieved evidence from the knowledge base.

        Returns:
            A plain-text comparison report containing grouped search results for
            each player, or a fallback message when no relevant information is found.
        """
        if not players:
            return "No players provided for comparison."
        response = "Comparing players:\n"
        for player in players:
            results = await SearchDocumentsService(session, player, sport=sport, limit=5)
            if results:
                response += f"\nStats and achievements for {player}:\n"
                for idx, (doc, score) in enumerate(results, start=1):
                    response += f"{idx}. {doc.content} (Source: {doc.source})\n"
                    cited_documents.append((doc.id, score))
            else:
                response += f"\nNo relevant information found for {player}.\n"
        return response

    async def fact_check(statement: str) -> str:
        """Search for evidence that supports or contradicts a sports-related statement.

        Use this tool when the user makes a claim that needs verification,
        correction, or evidence-based validation. It is especially useful for
        disputed facts, rankings, records, match outcomes, or historical claims.

        Args:
            statement: The sports claim or statement that needs to be checked.

        Returns:
            A numbered plain-text list of evidence snippets and their sources,
            or a fallback message when no relevant evidence is found.
        """
        search_results = await SearchDocumentsService(session, statement, sport=sport, limit=5)
        if not search_results:
            return "No relevant information found to fact-check the statement."
        response = "Fact-checking results:\n"
        for idx, (doc, score) in enumerate(search_results, start=1):
            response += f"{idx}. {doc.content} (Source: {doc.source})\n"
            cited_documents.append((doc.id, score))
        return response

    async def search_opposing_view(topic: str) -> str:
        """Find counterarguments or alternative perspectives on a sports topic.

        Use this tool when the response should challenge a claim, surface a
        different angle, or provide balance by looking for evidence that may
        weaken or complicate the current argument.

        Args:
            topic: The sports topic, claim, player, team, or debate that needs
                an opposing or alternative viewpoint.

        Returns:
            A numbered plain-text list of potentially opposing evidence and
            sources, or a fallback message when no relevant evidence is found.
        """
        search_results = await SearchDocumentsService(session, topic, sport=sport, limit=5)
        if not search_results:
            return "No relevant information found presenting opposing viewpoints."
        response = "Here are some perspectives that might present opposing viewpoints:\n"
        for idx, (doc, score) in enumerate(search_results, start=1):
            response += f"{idx}. {doc.content} (Source: {doc.source})\n"
            cited_documents.append((doc.id, score))
        return response

    async def search_memory(query: str) -> str:
        """Retrieve relevant context from the current conversation's stored memory.

        Use this tool when the answer depends on something previously discussed,
        remembered preferences, earlier conclusions, or prior conversation context
        from the same conversation thread.

        Args:
            query: The memory lookup query describing what prior context should
                be retrieved.

        Returns:
            A numbered plain-text list of relevant memory snippets and their
            source types, or a fallback message when no relevant memory is found.
        """
        search_results = await SearchConversationMemoryService(session, conversation_id, query, limit=5)
        if not search_results:
            return "No relevant memory found for the query."
        response = "Here are some relevant memories from past conversations:\n"
        for idx, memory in enumerate(search_results, start=1):
            response += f"{idx}. {memory.content} (Source Type: {memory.source_type})\n"
        return response

    async def ingest_and_search(query: str) -> str:
        """Ingest fresh information for a topic, then search the updated knowledge base.

        Use this tool when the existing knowledge base may be missing the topic
        or when fresher coverage is needed before answering. This tool first
        ingests new content and then performs the same document retrieval flow.

        Args:
            query: The topic to ingest and then search for fresh evidence.

        Returns:
            A numbered plain-text list of relevant snippets discovered after
            ingestion, or a fallback message when nothing relevant is found.
        """
        await run_ingestion(
            session=session,
            wiki_titles=[query],
            rss_urls=[],
            sport=sport
        )
        search_results = await SearchDocumentsService(session, query, sport=sport, limit=5)
        if not search_results:
            return "No relevant information found after ingestion."
        response = "Here are some relevant results after ingestion:\n"
        for idx, (doc, score) in enumerate(search_results, start=1):
            response += f"{idx}. {doc.content} (Source: {doc.source})\n"
            cited_documents.append((doc.id, score))
        return response
    
    async def get_historical_parallel(event: str) -> str:
        """Find historical sports event or moments that are similar or parallel to the current topic being discussed.
        
        Args:
            event(str): The sports event, moment, player, team, or storyline for which to find historical parallels.

        Returns:
            str: A numbered plain-text list of historical parallels with brief explanations and their sources, or a fallback message when no relevant parallels are found.
        """
        search_results = await SearchDocumentsService(session, event, sport=sport, limit=5)
        if not search_results:
            return "No relevant historical parallels found."
        response = "Here are some historical sports events or moments that might be parallel to the current topic:\n"
        for idx, (doc, score) in enumerate(search_results, start=1):
            response += f"{idx}. {doc.content} (Source: {doc.source})\n"
            cited_documents.append((doc.id, score))
        return response
    
    async def add_memory(content: str, source_type: str) -> str:
        """Store a key fact, conclusion, or important piece of information from the conversation into the memory for future reference.
        
        Args:
            content(str): The content to be stored in memory, such as a key fact, conclusion, or important piece of information from the conversation.
            source_type(str): The type of the memory source (e.g., user_statement, ai_response, fact, story, etc.) to provide context about the origin of the memory.
        Returns:
            str: A confirmation string indicating that the memory has been successfully stored, or an error message if the operation fails.
        """
        try:
            await AddConversationMemoryService(session, conversation_id, content, source_type, metadata={})
            return "Memory added successfully."
        except Exception:
            return "Failed to add memory."
            
    return ({
        "search_stats": search_stats,
        "search_articles": search_articles,
        "compare_players": compare_players,
        "fact_check": fact_check,
        "search_opposing_view": search_opposing_view,
        "search_memory": search_memory,
        "ingest_and_search": ingest_and_search,
        "get_historical_parallel": get_historical_parallel,
        "add_memory": add_memory,
    }, cited_documents)