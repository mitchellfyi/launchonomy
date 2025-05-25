from autogen_core import Agent

def create_agent(role_name: str, persona: str, primer: str):
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    return Agent(
      name=role_name,
      system_prompt=f"You are {role_name}, {persona}.\n\n{primer}",
      client=client
    )
