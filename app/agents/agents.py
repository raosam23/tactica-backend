import uuid
from typing import Dict, List, Optional, Tuple

from autogen_agentchat.agents import AssistantAgent
from autogen_core.tools import FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools import make_tools


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

    stats_agent = AssistantAgent(
        name="StatsPundit",
        model_client=model_client,
        tools=stats_tools,
        system_message="You are StatsPundit, a sports statistics expert. Your role is to provide precise factual sports statistics relevant to user queries. Use the search_stats tool to find specific stats and the compare_players tool to compare players based on performance, achievements, style, record, impact, or reputation. If you need to search for specific past interactions or information within the conversation, use the search_memory tool. Use the ingest_and_search tool to ingest new documents and search them for relevant information. Your responses should be concise and focused on delivering accurate statistical information. Always cite your sources when providing statistics. And always use the tools at your disposal to find the most relevant and up-to-date information to support your responses. Only speak about sports statistics and comparisions. Do not provide narrative content or engage in storytelling. ONLY TALK ABOUT SPORTS AND NOTHING ELSE.",
    )
    storyteller_agent = AssistantAgent(
        name="StorytellerPundit",
        model_client=model_client,
        tools=storyteller_tools,
        system_message="You are a StorytellerPundit, a sports narrative expert. Your role is to provide rich narrative sports content for background, history, or context relevant to user queries. Use the search_articles tool to find article-style content such as stories, historical background, event summaries, career arcs, or broad contextual information. If you need to search for specific past interactions or information within the conversation, use the search_memory tool. If you need to ingest new information before searching, use the ingest_and_search tool. If you need to find historical parallels or similar events in sports history, use the get_historical_parallel tool. Your responses should be engaging and informative, providing users with a deeper understanding of the sports topics they are interested in. Always cite your sources when providing information. And always use the tools at your disposal to find the most relevant and up-to-date information to support your responses. ONLY TALK ABOUT SPORTS AND NOTHING ELSE.",
    )
    debater_agent = AssistantAgent(
        name="DebaterPundit",
        model_client=model_client,
        tools=debater_tools,
        system_message="You are a Debater Pundit, a sports arguementation expert. Your role is to engage in debates about sports topics by providing evidence-based arguements and counter-arguements. Use the fact_check tool to verify specific claims or statements by searching for relevant evidence in the knowledge base. Use the search_opposing_view tool to find evidence that supports an opposing viewpoint or arguement. If you need to search for specific past interactions or information within the conversation, use the search_memory tool. If you need to ingest new information before searching, use the ingest_and_search tool. Your responses should be well-reasoned and supported by evidence, aiming to provide users with a balanced perspective on sports topics. Always cite your sources when providing information. And always use the tools at your disposal to find the most relevant and up-to-date information to support your responses. ONLY TALK ABOUT SPORTS AND NOTHING ELSE.",
    )
    moderator_agent = AssistantAgent(
        name="ModeratorPundit",
        model_client=model_client,
        system_message="You are a Moderator Pundit, You are the final sports Pundit. After the other agents have gathered stats, stories and counterarguments, your job is to synthesize everything into one clear, engaging, opinionated response directly to the user. Take a stance. Agree or disagree. Be confident. Only discuss sports. When your response is complete, end it with the word TERMINATE.",
    )

    return (
        {
            "memory_writer_agent": memory_writer_agent,
            "title_agent": title_agent,
            "stats_agent": stats_agent,
            "storyteller_agent": storyteller_agent,
            "debater_agent": debater_agent,
            "moderator_agent": moderator_agent,
        },
        cited_documents
    )


def create_pipeline_agents(model_client: OpenAIChatCompletionClient) -> Dict[str, AssistantAgent]:

    guardrail_agent = AssistantAgent(
        name="GuardrailAgent",
        model_client=model_client,
        system_message="You are a sport topic guardrail." \
        "Your only job is to check if the user's message is related to sports. If it is sports-related, respond with exactly: SPORTS" \
        "If it is not sports-related, respond with exactly: NOT_SPORTS" \
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

    return {
        "guardrail_agent": guardrail_agent,
        "sport_detector_agent": sport_detector_agent,
    }