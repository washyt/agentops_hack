import openai

def create_assistant(instructions):
    assistant = openai.beta.assistants.create(
        name="Form Filler",
        model="gpt-4o",
        instructions=(instructions),
        tools=[{"type": "code_interpreter"}]
    )
    print(f"✅ Assistant created: {assistant.id}")
    return assistant.id
