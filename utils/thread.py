import openai
import time

def create_thread_with_file(file_id):
    thread = openai.beta.threads.create()
    print(f" Thread started: {thread.id}")

    openai.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="Please help me fill out this form.",
        attachments=[
            {
                "file_id": file_id,
                "tools": [{"type": "code_interpreter"}]
            }
        ]
    )
    print("📬 Message with attachment sent.")
    return thread.id

def wait_for_run(thread_id, assistant_id):
    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )
    print(f"🏃 Assistant run started: {run.id}")

    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status in ["completed", "failed"]:
            return run_status.status
        time.sleep(1)
