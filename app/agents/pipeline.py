import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.agents.agents import create_pipeline_agents, create_pundit_agents
from app.agents.group_chat import create_pundit_team
from app.agents.model_client import create_model_client
from app.models import Conversation
from app.models.message import Role
from app.models.user import User
from app.services.message_service import (CreateMessageCitationService,
                                          CreateMessageService,
                                          GetMessagesService)


async def run_chat_pipeline(
    session: AsyncSession,
    conversation_id: uuid.UUID,
    user_message: str,
    user: User,
    sport: Optional[str] = None
) -> str:
    model_client = create_model_client()

    # Create pipeline agents that does not need sport
    pipeline_agents = create_pipeline_agents(model_client)
    
    guardrail_result = await pipeline_agents["guardrail_agent"].run(task=user_message)
    guardrail_response = guardrail_result.messages[-1].content.strip().upper()

    if "NOT_SPORTS" in guardrail_response:
        return "I'm only here to talk about sports! Please ask me a sports-related question or make a sports-related statement."
    
    if sport is None:
        sport_result = await pipeline_agents["sport_detector_agent"].run(task=user_message)
        detected_sport = sport_result.messages[-1].content.strip().lower()
    else:
        detected_sport = sport.strip().lower()

    if detected_sport == "general":
        detected_sport = None
    
    # Get N past messages for context
    messages = await GetMessagesService(session, user, conversation_id)
    messages_for_context = messages[-10:] if len(messages) > 10 else messages

    # Create user message in database
    await CreateMessageService(session, conversation_id, Role.USER, user_message)

    # Create pundit agents that may need sport
    pundit_agent, cited_documents = await create_pundit_agents(session, conversation_id, detected_sport, model_client)
    team = await create_pundit_team(pundit_agent, model_client)

    if messages_for_context:
        context = "\n\n".join([f"{message.role.value.capitalize()}: {message.content}" for message in messages_for_context])
        task = (
            "Here are the past few messages in the conversation for context:\n\n"
            f"{context}\n\n"
            f"Current user message: {user_message}"
        )
    else:
        task = user_message

    result = await team.run(task=task)

    final_response = ""
    for message in reversed(result.messages):
        if hasattr(message, "source") and message.source == "ModeratorPundit":
            final_response = message.content.replace("TERMINATE", "").strip()
            break
    
    conversation_summary = f"User: {user_message}\n\nAssistant: {final_response}"

    if not final_response:
        final_response = "Sorry, I wasn't able to generate a response. Please try again."

    # Create assistant message in database
    message = await CreateMessageService(session, conversation_id, Role.ASSISTANT, final_response)
    if cited_documents:
        await CreateMessageCitationService(session, message.id, cited_documents)

    await pundit_agent["memory_writer_agent"].run(task=conversation_summary,)

    result = await session.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    if conversation and not conversation.title:
        title_result = await pundit_agent["title_agent"].run(
            task=f"User: {user_message}\n\nAssistant: {final_response}\n\nGenerate a short, catchy title that captures the main topic of this conversation. Maximum 6 words. No punctuation,",
        )

        generated_title = title_result.messages[-1].content.strip()
        conversation.title = generated_title
        session.add(conversation)
        await session.commit()


    return final_response
