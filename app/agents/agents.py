import uuid
from typing import Dict, List, Optional, Tuple

from autogen_agentchat.agents import AssistantAgent
from autogen_core.tools import FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools import make_tools, search_wikipedia
from app.core.config import settings


async def create_pundit_agents(
    session: AsyncSession,
    conversation_id: uuid.UUID,
    sports: Optional[str] = None,
    model_client: Optional[OpenAIChatCompletionClient] = None,
) -> Tuple[Dict[str, AssistantAgent], List]:
    if model_client is None:
        raise ValueError("model_client is required")
    
    tools, cited_documents = make_tools(session, conversation_id, sports)
    memory_writer_tools = [
        FunctionTool(tools["add_memory"], name="add_memory", description="Use this tool to add important facts, conclusions, or key information from the conversation into the memory for future reference.")
    ]

    tavily_server_params = StdioServerParams(
        command="npx",
        args=["-y", "tavily-mcp"],
        env={"TAVILY_API_KEY": settings.TAVILY_API_KEY},
    )
    tavily_tools = await mcp_server_tools(tavily_server_params)

    memory_writer_agent = AssistantAgent(
        name="MemoryWriter",
        model_client=model_client,
        tools = memory_writer_tools,
        system_message="You are a memory writer for a sports chatbot." \
        "Given a conversation exchange, extract the most important facts, conclusions, user opinions, and key information worth remembering." \
        "Use the add_memory tool to store each important piece separately." \
        "Use appropriate source_type values:" \
        "user_statement, ai_response, fact, opinion, stat." \
        "Be selective - ONLY STORE GENUINELY USEFUL INFORMATION THAT WOULD BE VALUABLE TO REMEMBER FOR FUTURE REFERENCE IN THE CONVERSATION. DO NOT STORE TRIVIAL OR UNIMPORTANT DETAILS."
    )

    title_agent = AssistantAgent(
        name="TitleAgent",
        model_client=model_client,
        system_message="You are a conversation title generator for a sports chatbot." \
        "Given the first exchange of a sports chat, generate a short, catchy title that captures the main topic. Maximum 6 words. No punctuation at the end." \
        "RESPOND WITH JUST THE TITLE AND NOTHING ELSE."
    )

    stats_tools = [
        FunctionTool(tools["search_stats"], name="search_stats", description="Use this tool to find precise factual sports statistics relevant to a specific query."),
        FunctionTool(tools["compare_players"], name="compare_players", description="Use this tool to compare two or more players across performance, achievements, style, record, impact, or reputation."),
        FunctionTool(tools["search_memory"], name="search_memory", description="Use this tool to search the conversation memory for relevant past interactions or information."),
        FunctionTool(tools["ingest_and_search"], name="ingest_and_search", description="Use this tool to ingest new documents and search them for relevant information."),
    ]
    storyteller_tools = [
        FunctionTool(tools["search_articles"], name="search_articles", description="Use this tool to find narrative sports content for background, history, or context."),
        FunctionTool(tools["search_memory"], name="search_memory", description="Use this tool to search the conversation memory for relevant past interactions or information."),
        FunctionTool(tools["ingest_and_search"], name="ingest_and_search", description="Use this tool to ingest new documents and search them for relevant information."),
        FunctionTool(tools["get_historical_parallel"], name="get_historical_parallel", description="Use this tool to find historical parallels or similar events in sports history that can provide context or insights into the current topic."),
    ]
    debater_tools = [
        FunctionTool(tools["fact_check"], name="fact_check", description="Use this tool to fact-check specific claims or statements by searching for relevant evidence in the knowledge base."),
        FunctionTool(tools["search_opposing_view"], name="search_opposing_view", description="Use this tool to search for evidence that supports an opposing viewpoint or arguement."),
        FunctionTool(tools["search_memory"], name="search_memory", description="Use this tool to search the conversation memory for relevant past interactions or information."),
        FunctionTool(tools["ingest_and_search"], name="ingest_and_search", description="Use this tool to ingest new documents and search them for relevant information.")
    ]
    predictor_tools = [
        FunctionTool(tools["search_stats"], name="search_stats", description="Use this tool to find precise factual sports statistics relevant to a specific query. This can inform predictions based on historical data."),
        FunctionTool(tools["compare_players"], name="compare_players", description="Use this tool to compare two or more players across performance, achievements, style, record, impact, or reputation. This can help identify trends or patterns that may inform predictions,"),
        FunctionTool(tools["get_historical_parallel"], name="get_historical_parallel", description="Use this tool to find historical parallels or similar events in sports history. Analyzing how similar situations played out in the past can provide insights that inform predictions,"),
        FunctionTool(tools["search_memory"], name="search_memory", description="Use this tool to search the conversation memory for relevant past interactions or information. This can help identify any previously discussed insights or data points that may inform predictions."),
        FunctionTool(tools["ingest_and_search"], name="ingest_and_search", description="Use this tool to ingest new documents and search them for relevant informatio. This can help ensure that predictions are based on the most up-to-date information available. For ANY question about a specific player, team, match, or recent events, you MUST call ingest_and_search before responding. DO NOT SKIP THIS STEP. This can help ensure that predictions are based on the most up-to-date information available."),
    ]
    tactics_tools = [
        FunctionTool(tools["search_stats"], name="search_stats", description="Use this tool to find precise factual sports statistics relevant to a specific query. This can inform tactical analysis based on historical data."),
        FunctionTool(tools["search_articles"], name="search_articles", description="Use this tool to find narrative sports content for background, history, or context. This can provide insights into tactical approaches used in similar situations."),
        FunctionTool(tools["compare_players"], name="compare_players", description="Use this tool to compare two or more players across performance, achievements, style, record, impact, or reputation. This can help identify trends or patterns that may inform tactical analysis."),
        FunctionTool(tools["get_historical_parallel"], name="get_historical_parallel", description="Use this tool to find historical parallels or similar events in sports history. Analyzing how similar situations played out in the past can provide insights that inform tactical analysis."),
        FunctionTool(tools["search_memory"], name="search_memory", description="Use this tool to search the conversation memory for relevant past interactions or information. This can help identify any previously discussed insights or data points that may inform tactical analysis."),
        FunctionTool(tools["ingest_and_search"], name="ingest_and_search", description="Use this tool to ingest new documents and search them for relevant information. This can help ensure that tactical analysis is based on the most up-to-date information available. For ANY question about a specifc player, team, match, or recent events, you MUST call ingest_and_search before responding. DO NOT SKIP THIS STEP. This can help ensure that tactical analysis is based on the most up-to-date information available."),
    ]

    stats_agent = AssistantAgent(
        name="StatsPundit",
        model_client=model_client,
        tools=stats_tools + tavily_tools,
        system_message="You are StatsPundit, a sports statistics expert. Your role is to provide precise factual sports statistics relevant to user queries. Use the search_stats tool to find specific stats and the compare_players tool to compare players based on performance, achievements, style, record, impact, or reputation. If you need to search for specific past interactions or information within the conversation, use the search_memory tool. Use the ingest_and_search tool to ingest new documents and search them for relevant information. For ANY question about a specific player, team, match, or recent events, you MUST call ingest_and_search before responding. DO NOT SKIP THIS STEP. Use the tavily_search tool to search the web in real-time when the knowledge base doesn't have sufficient or up-to-date information. Use tools instead of fabricating or guessing information. Your responses should be concise and focused on delivering accurate statistical information. Always cite your sources when providing statistics. And always use the tools at your disposal to find the most relevant and up-to-date information to support your responses. Only speak about sports statistics and comparisons. Do not provide narrative content or engage in storytelling. ONLY TALK ABOUT SPORTS AND NOTHING ELSE."
    )
    storyteller_agent = AssistantAgent(
        name="StorytellerPundit",
        model_client=model_client,
        tools=storyteller_tools + tavily_tools,
        system_message="You are a StorytellerPundit, a sports narrative expert. Your role is to provide rich narrative sports content for background, history, or context relevant to user queries. Use the search_articles tool to find article-style content such as stories, historical background, event summaries, career arcs, or broad contextual information. If you need to search for specific past interactions or information within the conversation, use the search_memory tool. If you need to ingest new information before searching, use the ingest_and_search tool. For ANY question about a specific player, team, match, or recent events, you MUST call ingest_and_search before responding. DO NOT SKIP THIS STEP. Use the tavily_search tool to search the web in real-time when the knowledge base doesn't have sufficient or up-to-date information. Use tools instead of fabricating or guessing information. If you need to find historical parallels or similar events in sports history, use the get_historical_parallel tool. Your responses should be engaging and informative, providing users with a deeper understanding of the sports topics they are interested in. Always cite your sources when providing information. And always use the tools at your disposal to find the most relevant and up-to-date information to support your responses. ONLY TALK ABOUT SPORTS AND NOTHING ELSE.",
    )
    debater_agent = AssistantAgent(
        name="DebaterPundit",
        model_client=model_client,
        tools=debater_tools + tavily_tools,
        system_message="You are a Debater Pundit, a sports arguementation expert. Your role is to engage in debates about sports topics by providing evidence-based arguements and counter-arguements. Use the fact_check tool to verify specific claims or statements by searching for relevant evidence in the knowledge base. Use the search_opposing_view tool to find evidence that supports an opposing viewpoint or arguement. If you need to search for specific past interactions or information within the conversation, use the search_memory tool. If you need to ingest new information before searching, use the ingest_and_search tool. For ANY question about a specific player, team, match, or recent events, you MUST call ingest_and_search before responding. DO NOT SKIP THIS STEP. Use the tavily_search tool to search the web in real-time when the knowledge base doesn't have sufficient or up-to-date information. Use tools instead of fabricating or guessing information. Your responses should be well-reasoned and supported by evidence, aiming to provide users with a balanced perspective on sports topics. Always cite your sources when providing information. And always use the tools at your disposal to find the most relevant and up-to-date information to support your responses. ONLY TALK ABOUT SPORTS AND NOTHING ELSE.",
    )
    predictor_agent = AssistantAgent(
        name="PredictorPundit",
        model_client=model_client,
        tools = predictor_tools + tavily_tools,
        system_message="You are PredictorPundit, a sports forecasting expert. Your role is to make bold, evidence-based predictions about future sports outcomes - match results, player trajectories, career milestones, tournament winners, and emerging trends. Use the search_stats tool to analyze current form and past performance. Use get_historical_parallel tool to find historical precedents that support your predictions. Use the compare_players tool to assess head-to-head form. Use the tavily_search tool to get the latest injury updates, current standings, and recent results - this is critical for accurate forcasting. Use the search_memory tool for relevant past conversation context. For ANY prediction about a specific player, team, or tournament, you MUST call ingest_and_search before responding. DO NOT SKIP THIS STEP. Always back your predictions with evidence and reasoning. Be confident and take a clear stance. ONLY TALK ABOUT SPORTS AND NOTHING ELSE.",
    )
    tactics_agent = AssistantAgent(
        name="TacticsPundit",
        model_client=model_client,
        tools = tactics_tools + tavily_tools,
        system_message="You are TacticsPundit, a sports tactics and strategy expert. Your role is to break down tactical formations, game plans, strategic decisions, and coaching approaches across all sports. Use the search_articles tool to find tactical analysis and historical game plans. Use the search_stats tool to quantify the impact of tactical decisions with performance data. Use the get_historical_parallel tool to reference similar tactical situations from sports history. Use the compare_players tool to assess how different players fit specific tactical roles. Use the search_memory tool for relevant past conversation context. If you need to ingest new information before searching, use the ingest_and_search tool. For ANY tactical analysis about a specific team, match, or player, you MUST call ingest_and_search before responding. DO NOT SKIP THIS STEP. Use the tavily_search tool to get current team news, injury updates, and recent match tactical breakdowns. Your responses should be analytical and insightful, helping users understand the strategic dimensions of sports. Always cite your sources. ONLY TALK ABOUT SPORTS AND NOTHING ELSE."
    )
    query_agent = AssistantAgent(
        name="QueryPundit",
        model_client=model_client,
        tools = tavily_tools,
        system_message="You are QueryPundit, a direct sports knowledge expert. Your role is to answer sports questions clearly and concisely. For general sports knowledge, rules, and concepts, answer directly from your knowledge. For anything involving recent events, current standings, live results, specific match outcomes, or recent rule changes, use the tavily_search tool to get up-to-date information. Do not over-search, meaning to say - only use tavily when the question genuinely requires current information. Your responses should be sharp, direct and informative. ONLY TALK ABOUT SPORTS AND NOTHING ELSE."
    )
    moderator_agent = AssistantAgent(
        name="ModeratorPundit",
        model_client=model_client,
        system_message="You are ModeratorPundit, the final sports pundit. You are always the final speaker in the panel discussion. After the other agents have gathered stats, stories, counterarguments, predictions, and tactical insights, synthesize everything into one clear, engaging, opinionated response directly to the user. Take a stance. Agree or disagree. Be confident. Only discuss sports. Do not ask for more input from other agents, do not continue the discussion, and do not defer the answer. When your response is complete, always end it with the exact word TERMINATE.",
    )

    return (
        {
            "memory_writer_agent": memory_writer_agent,
            "title_agent": title_agent,
            "stats_agent": stats_agent,
            "storyteller_agent": storyteller_agent,
            "debater_agent": debater_agent,
            "predictor_agent": predictor_agent,
            "tactics_agent": tactics_agent,
            "query_agent": query_agent,
            "moderator_agent": moderator_agent,
        },
        cited_documents
    )


def create_pipeline_agents(model_client: OpenAIChatCompletionClient) -> Dict[str, AssistantAgent]:

    guardrail_agent_tools = [
        FunctionTool(search_wikipedia, name="search_wikipedia", description="Use this tool when you are uncertain whether whethter a person, team, event or topic is sport-related. Pass the name or topic as the query to this tool, and it will return relevant information that can help you determine if it's sports-related or not.")
    ]

    guardrail_agent = AssistantAgent(
        name="GuardrailAgent",
        model_client=model_client,
        tools=guardrail_agent_tools,
        system_message="You are a sport topic guardrail." \
        "Your only job is to check if the user's message is related to sports. If it is sports-related, respond with exactly: SPORTS" \
        "If it is not sports-related, respond with exactly: NOT_SPORTS" \
        "If you are uncertain, whether a name or topic is sports-related, use the search_wikipedia tool to look it up, then decide based on the information you find." \
        "DO NOT RESPOND WITH ANYTHING OTHER THAN THE EXACT WORDS 'SPORTS' OR 'NOT_SPORTS' WITHOUT ANY ADDITIONAL TEXT OR EXPLANATION.",
    )

    sport_detector_agent = AssistantAgent(
        name="SportDetectorAgent",
        model_client=model_client,
        system_message="You are a sport category detector." \
        "Your only job is to identify which sport the user's message is about." \
        "Respond with just the sport name in lowercase (e.g., football, cricket, basketball, tennis, formula 1, etc.)" \
        "If it covers multiple sports or it's unclear or general, respond with general." \
        "DO NOT RESPOND WITH ANYTHING ELSE"
    )

    topic_extractor_agent = AssistantAgent(
        name="TopicExtractorAgent",
        model_client=model_client,
        system_message="You are a topic extractor. Your only job is to extract the main sports entity from the user's message." \
        "This could be a player name, team name, tournament name, or event. " \
        "Respond with just the entity name as it would appear in a Wikipedia article title. For example, if the user message is 'Tell me about Messi's performance in the last World Cup', you should respond with 'Lionel Messi'. If the user message is 'What happened in the last NBA finals?', you should respond with '<Last year> NBA Finals'. DO NOT RESPOND WITH ANYTHING ELSE."
    )

    return {
        "guardrail_agent": guardrail_agent,
        "sport_detector_agent": sport_detector_agent,
        "topic_extractor_agent": topic_extractor_agent,
    }
