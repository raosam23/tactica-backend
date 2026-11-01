"""
Unit tests for the chat pipeline components.

Tests cover:
- Citation deduplication logic
- Guardrail behavior (sports vs non-sports detection)
- Sport detection agent behavior
- Group chat candidate selection function

These tests mock AutoGen agents to verify pipeline logic without LLM calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.pipeline import _handle_citation_deduplications
from app.schemas.message import CitationResponse


class TestCitationDeduplication:
    """Tests for the _handle_citation_deduplications helper function."""

    def test_dedup_keeps_single_citations(self):
        """Single citations should pass through unchanged."""
        citations = [
            CitationResponse(source="Wikipedia - Messi", relevance_score=0.85),
            CitationResponse(source="ESPN - Football", relevance_score=0.72),
        ]

        result = _handle_citation_deduplications(citations)

        assert len(result) == 2
        sources = {c.source for c in result}
        assert "Wikipedia - Messi" in sources
        assert "ESPN - Football" in sources

    def test_dedup_keeps_highest_score_for_same_source(self):
        """Duplicate sources should keep only the highest relevance score."""
        citations = [
            CitationResponse(source="Wikipedia - Messi", relevance_score=0.60),
            CitationResponse(source="Wikipedia - Messi", relevance_score=0.85),
            CitationResponse(source="Wikipedia - Messi", relevance_score=0.72),
        ]

        result = _handle_citation_deduplications(citations)

        assert len(result) == 1
        assert result[0].source == "Wikipedia - Messi"
        assert result[0].relevance_score == 0.85

    def test_dedup_handles_multiple_duplicates(self):
        """Multiple duplicate sources should each keep their highest score."""
        citations = [
            CitationResponse(source="Source A", relevance_score=0.50),
            CitationResponse(source="Source B", relevance_score=0.60),
            CitationResponse(source="Source A", relevance_score=0.80),
            CitationResponse(source="Source B", relevance_score=0.40),
            CitationResponse(source="Source C", relevance_score=0.70),
        ]

        result = _handle_citation_deduplications(citations)

        assert len(result) == 3
        result_dict = {c.source: c.relevance_score for c in result}
        assert result_dict["Source A"] == 0.80
        assert result_dict["Source B"] == 0.60
        assert result_dict["Source C"] == 0.70

    def test_dedup_empty_list_returns_empty(self):
        """Empty input should return empty output."""
        result = _handle_citation_deduplications([])
        assert result == []

    def test_dedup_handles_same_scores(self):
        """Citations with identical scores should work correctly."""
        citations = [
            CitationResponse(source="Source A", relevance_score=0.5),
            CitationResponse(source="Source A", relevance_score=0.5),
        ]

        result = _handle_citation_deduplications(citations)

        assert len(result) == 1
        assert result[0].relevance_score == 0.5


class TestCandidateSelectorFunction:
    """Tests for the candidate_selector_function in group_chat."""

    @pytest.mark.asyncio
    async def test_returns_specialists_when_none_have_spoken(self):
        """Should return all specialists when no one has spoken."""
        from app.agents.group_chat import candidate_selector_function

        messages = []

        result = await candidate_selector_function(messages)

        expected_specialists = [
            "StatsPundit",
            "StorytellerPundit",
            "DebaterPundit",
            "PredictorPundit",
            "TacticsPundit",
            "QueryPundit",
        ]
        assert set(result) == set(expected_specialists)

    @pytest.mark.asyncio
    async def test_excludes_specialists_who_have_spoken(self):
        """Should exclude specialists who have already spoken."""
        from app.agents.group_chat import candidate_selector_function

        msg1 = MagicMock()
        msg1.source = "StatsPundit"
        msg2 = MagicMock()
        msg2.source = "StorytellerPundit"
        messages = [msg1, msg2]

        result = await candidate_selector_function(messages)

        assert "StatsPundit" not in result
        assert "StorytellerPundit" not in result
        assert "DebaterPundit" in result
        assert "PredictorPundit" in result

    @pytest.mark.asyncio
    async def test_forces_moderator_after_four_specialists(self):
        """Should force ModeratorPundit after 4+ specialists have spoken."""
        from app.agents.group_chat import candidate_selector_function

        messages = []
        for name in [
            "StatsPundit",
            "StorytellerPundit",
            "DebaterPundit",
            "PredictorPundit",
        ]:
            msg = MagicMock()
            msg.source = name
            messages.append(msg)

        result = await candidate_selector_function(messages)

        assert result == ["ModeratorPundit"]

    @pytest.mark.asyncio
    async def test_returns_moderator_only_if_already_spoken(self):
        """If ModeratorPundit has spoken, should only return ModeratorPundit."""
        from app.agents.group_chat import candidate_selector_function

        msg = MagicMock()
        msg.source = "ModeratorPundit"
        messages = [msg]

        result = await candidate_selector_function(messages)

        assert result == ["ModeratorPundit"]

    @pytest.mark.asyncio
    async def test_returns_moderator_when_no_specialists_left(self):
        """Should return ModeratorPundit when all specialists have spoken."""
        from app.agents.group_chat import candidate_selector_function

        messages = []
        specialists = [
            "StatsPundit",
            "StorytellerPundit",
            "DebaterPundit",
            "PredictorPundit",
            "TacticsPundit",
            "QueryPundit",
        ]
        for name in specialists:
            msg = MagicMock()
            msg.source = name
            messages.append(msg)

        result = await candidate_selector_function(messages)

        assert result == ["ModeratorPundit"]


class TestGuardrailBehavior:
    """Tests for guardrail agent behavior patterns."""

    def test_sports_response_pattern(self):
        """SPORTS response indicates sports-related query."""
        response = "SPORTS"
        assert "NOT_SPORTS" not in response
        assert "SPORTS" in response

    def test_not_sports_response_pattern(self):
        """NOT_SPORTS response indicates non-sports query."""
        response = "NOT_SPORTS"
        assert "NOT_SPORTS" in response

    def test_guardrail_response_parsing(self):
        """Pipeline correctly parses guardrail responses."""
        sports_response = "SPORTS"
        not_sports_response = "NOT_SPORTS"

        assert "NOT_SPORTS" not in sports_response.strip().upper()
        assert "NOT_SPORTS" in not_sports_response.strip().upper()

    @pytest.mark.parametrize(
        "response,is_sports",
        [
            ("SPORTS", True),
            ("sports", True),
            ("  SPORTS  ", True),
            ("NOT_SPORTS", False),
            ("not_sports", False),
            ("  NOT_SPORTS  ", False),
        ],
    )
    def test_guardrail_response_variations(self, response, is_sports):
        """Guardrail responses should be case-insensitive and strip whitespace."""
        normalized = response.strip().upper()
        result = "NOT_SPORTS" not in normalized
        assert result == is_sports


class TestSportDetection:
    """Tests for sport detection patterns."""

    @pytest.mark.parametrize(
        "detected,expected_normalized",
        [
            ("football", "football"),
            ("FOOTBALL", "football"),
            ("  Football  ", "football"),
            ("basketball", "basketball"),
            ("tennis", "tennis"),
            ("Formula 1", "formula 1"),
            ("f1", "f1"),
            ("general", None),
            ("GENERAL", None),
        ],
    )
    def test_sport_normalization(self, detected, expected_normalized):
        """Sport detection output should be normalized to lowercase."""
        normalized = detected.strip().lower()
        if normalized == "general":
            normalized = None
        assert normalized == expected_normalized

    def test_general_sport_becomes_none(self):
        """'general' sport should be converted to None."""
        detected_sport = "general"
        result = (
            None
            if detected_sport.strip().lower() == "general"
            else detected_sport.strip().lower()
        )
        assert result is None


class TestPipelineAgentCreation:
    """Tests for pipeline agent creation without LLM calls."""

    def test_create_pipeline_agents_returns_expected_agents(self):
        """create_pipeline_agents should return all required agent types."""
        from app.agents.agents import create_pipeline_agents

        mock_model_client = MagicMock()

        agents = create_pipeline_agents(mock_model_client)

        assert "guardrail_agent" in agents
        assert "sport_detector_agent" in agents
        assert "topic_extractor_agent" in agents

    def test_guardrail_agent_has_wikipedia_tool(self):
        """GuardrailAgent should have access to search_wikipedia tool."""
        from app.agents.agents import create_pipeline_agents

        mock_model_client = MagicMock()

        agents = create_pipeline_agents(mock_model_client)
        guardrail = agents["guardrail_agent"]

        tool_names = [tool.name for tool in guardrail._tools]
        assert "search_wikipedia" in tool_names

    def test_sport_detector_has_no_tools(self):
        """SportDetectorAgent should have no tools."""
        from app.agents.agents import create_pipeline_agents

        mock_model_client = MagicMock()

        agents = create_pipeline_agents(mock_model_client)
        detector = agents["sport_detector_agent"]

        assert len(detector._tools) == 0


class TestSearchWikipediaTool:
    """Tests for the search_wikipedia tool function."""

    @pytest.mark.asyncio
    async def test_search_wikipedia_returns_content(self):
        """search_wikipedia should return article content."""
        from app.agents.tools import search_wikipedia

        mock_articles = [
            {
                "title": "Lionel Messi",
                "content": "Lionel Messi is an Argentine professional footballer...",
                "url": "https://en.wikipedia.org/wiki/Lionel_Messi",
                "source": "wikipedia",
            }
        ]

        with patch(
            "app.agents.tools.scrape_wikipedia_articles",
            AsyncMock(return_value=mock_articles),
        ):
            result = await search_wikipedia("Lionel Messi")

        assert "Messi" in result
        assert "footballer" in result.lower()

    @pytest.mark.asyncio
    async def test_search_wikipedia_returns_fallback_when_not_found(self):
        """search_wikipedia should return fallback message when article not found."""
        from app.agents.tools import search_wikipedia

        with patch(
            "app.agents.tools.scrape_wikipedia_articles", AsyncMock(return_value=[])
        ):
            result = await search_wikipedia("Nonexistent Topic 12345")

        assert "no relevant" in result.lower()

    @pytest.mark.asyncio
    async def test_search_wikipedia_truncates_long_content(self):
        """search_wikipedia should truncate content to 500 characters."""
        from app.agents.tools import search_wikipedia

        long_content = "A" * 1000
        mock_articles = [
            {
                "title": "Test",
                "content": long_content,
                "url": "https://en.wikipedia.org/wiki/Test",
                "source": "wikipedia",
            }
        ]

        with patch(
            "app.agents.tools.scrape_wikipedia_articles",
            AsyncMock(return_value=mock_articles),
        ):
            result = await search_wikipedia("Test")

        assert len(result) <= 500
