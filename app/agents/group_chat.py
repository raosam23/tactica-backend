from typing import Dict

from autogen_agentchat.conditions import (MaxMessageTermination,
                                          TextMentionTermination)
from autogen_agentchat.teams import SelectorGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def candidate_selector_function(messages):
    specialist_names = [
        "StatsPundit",
        "StorytellerPundit",
        "DebaterPundit",
        "PredictorPundit",
        "TacticsPundit",
        "QueryPundit"
    ]

    spoken_agents = {message.source for message in messages if hasattr(message, "source")}

    if "ModeratorPundit" in spoken_agents:
        return ["ModeratorPundit"]
    
    spoken_specialists = [name for name in specialist_names if name in spoken_agents]

    if len(spoken_specialists) >= 4:
        return ["ModeratorPundit"]
    
    remaining_specialists = [name for name in specialist_names if name not in spoken_agents]
    
    if not remaining_specialists:
        return ["ModeratorPundit"]
    
    return remaining_specialists

async def create_pundit_team(
    agents: Dict,
    model_client: OpenAIChatCompletionClient,
) -> SelectorGroupChat:
    
    stats_agent = agents["stats_agent"]
    storyteller_agent = agents["storyteller_agent"]
    debater_agent = agents["debater_agent"]
    predictor_agent = agents["predictor_agent"]
    tactics_agent = agents["tactics_agent"]
    query_agent = agents["query_agent"]
    moderator_agent = agents["moderator_agent"]

    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(20)

    selector_prompt = """
        You are managing a sports discussion panel. The following roles are available to you:
        {roles}

        Rules:
        1. Each agent should speak at most once. Do not select an agent that has already spoken in the discussion.
        2. Only select an agent if they are relevant to the question and can provide a meaningful contribution.
        3. Once atleast 4 specialists have spoken, you MUST select ModeratorPundit to synthesize and conclude the discussion.

        {history}

        Select the next role from {participants} to play. Only return the role.
    """

    team = SelectorGroupChat(
        participants=[stats_agent, storyteller_agent, debater_agent, predictor_agent, tactics_agent, query_agent, moderator_agent],
        model_client=model_client,
        selector_prompt=selector_prompt,
        candidate_func=candidate_selector_function,
        termination_condition=termination
    )

    return team
