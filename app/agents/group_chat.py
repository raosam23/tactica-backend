from typing import Dict

from autogen_agentchat.conditions import (MaxMessageTermination,
                                          TextMentionTermination)
from autogen_agentchat.teams import SelectorGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def create_pundit_team(
    agents: Dict,
    model_client: OpenAIChatCompletionClient,
) -> SelectorGroupChat:
    
    stats_agent = agents["stats_agent"]
    storyteller_agent = agents["storyteller_agent"]
    debater_agent = agents["debater_agent"]
    moderator_agent = agents["moderator_agent"]

    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(20)

    team = SelectorGroupChat(
        participants=[stats_agent, storyteller_agent, debater_agent, moderator_agent],
        model_client=model_client,
        termination_condition=termination
    )

    return team
