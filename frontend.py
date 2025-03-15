import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import threading
import openai
import agentops
import os
import json
from dotenv import load_dotenv
from utils.assistant import create_assistant
from utils.file import upload_file
from utils.thread import create_thread_with_file, wait_for_run

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
agentops.init(os.getenv("AGENTOPS_API_KEY"))

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🩺 Form Assistant")
        self.root.configure(bg="#1e1e2f")

        self.main_frame = tk.Frame(root, bg="#1e1e2f")
        self.main_frame.pack(padx=30, pady=30)

        self.title_label = tk.Label(self.main_frame, text="Form Assistant", font=("Helvetica", 20, "bold"), fg="#00ffe0", bg="#1e1e2f")
        self.title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))

        self.chat_log = scrolledtext.ScrolledText(
            self.main_frame, wrap=tk.WORD, width=80, height=25, state="disabled",
            bg="#282c34", fg="#dcdcdc", font=("Courier New", 12), relief=tk.FLAT, borderwidth=10
        )
        self.chat_log.grid(row=1, column=0, columnspan=2, pady=(0, 15))

        self.input_box = tk.Entry(self.main_frame, width=70, font=("Courier New", 12), bg="#20232a", fg="#dcdcdc",
                                   insertbackground="#00ffe0", relief=tk.FLAT)
        self.input_box.grid(row=2, column=0, sticky="we", padx=(0, 10))
        self.input_box.bind("<Return>", self.send_message)

        self.send_button = tk.Button(
            self.main_frame, text="Send", width=10, bg="#00ffe0", fg="#1e1e2f",
            font=("Helvetica", 11, "bold"), activebackground="#00d6c5",
            command=self.send_message, relief=tk.FLAT
        )
        self.send_button.grid(row=2, column=1, sticky="e")

        self.progress_bar = ttk.Progressbar(self.main_frame, mode="indeterminate")
        self.progress_bar.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="we")
        self.progress_bar.grid_remove()

        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar", thickness=5, troughcolor="#1e1e2f", background="#00ffe0", bordercolor="#1e1e2f")

        self.assistant_id = None
        self.thread_id = None
        self.responses = {}
        self.last_question = ""

        self.startup_thread = threading.Thread(target=self.setup_assistant)
        self.startup_thread.start()

    def setup_assistant(self):
        try:
            self.append_chat("🛠 Creating assistant...")
            self.assistant_id = create_assistant(instructions=(
                "You are a helpful form-filling assistant. A user will upload a form. Do your best to interpret the form regardless of type.\n"
                "Immediately greet the user and begin by asking the user questions based on what is required to fill the form.\n"
                "Avoid listing all the required fields up front. Instead, ask one question at a time immediately after the form has been uploaded.\n"
                "Ask the least amount of questions needed to gather all information needed to fill out the form.\n"
                "Once you have all information, output a JSON with each question as an object and the extrapolated answer as a key in the proper format, the first object and value should be filled_form and true."
            ))
            self.append_chat("✅ Assistant ready. Please select a form.")
            self.start_upload()
        except Exception as e:
            self.append_chat(f"❌ Failed to create assistant: {e}")
            try:
                agentops.end_session("Fail")
            except:
                pass

    def start_upload(self):
        filepath = filedialog.askopenfilename(filetypes=[("PDF or Image", "*.pdf *.png *.jpg *.jpeg")])
        if not filepath:
            self.append_chat("❌ No file selected. Exiting.")
            self.root.quit()
            return

        self.append_chat("📤 Uploading form...")
        self.show_loading()
        threading.Thread(target=self.initialize_assistant, args=(filepath,)).start()

    def show_loading(self):
        self.progress_bar.grid()
        self.progress_bar.start(10)
        self.send_button.config(state="disabled")
        self.input_box.config(state="disabled")

    def hide_loading(self):
        self.progress_bar.stop()
        self.progress_bar.grid_remove()
        self.send_button.config(state="normal")
        self.input_box.config(state="normal")
        self.input_box.focus()

    def initialize_assistant(self, filepath):
        try:
            file_id = upload_file(filepath)
            self.append_chat("✅ File uploaded. Starting thread...")
            self.thread_id = create_thread_with_file(file_id)
            self.append_chat("🧵 Thread created. Asking first question...")
            wait_for_run(self.thread_id, self.assistant_id)
            self.get_response()
        except Exception as e:
            self.append_chat(f"❌ Initialization error: {e}")
            try:
                agentops.end_session("Fail")
            except:
                pass

    def send_message(self, event=None):
        user_msg = self.input_box.get().strip()
        if not user_msg:
            return

        self.input_box.delete(0, tk.END)
        self.append_chat(f"🧑 You: {user_msg}")
        self.responses[self.last_question] = user_msg

        try:
            openai.beta.threads.messages.create(
                thread_id=self.thread_id,
                role="user",
                content=user_msg
            )

            self.show_loading()
            threading.Thread(target=self.continue_chat).start()
        except Exception as e:
            self.append_chat(f"❌ Failed to send message: {e}")
            try:
                agentops.end_session("Fail")
            except:
                pass

    def continue_chat(self):
        wait_for_run(self.thread_id, self.assistant_id)
        self.get_response()

    def get_response(self):
        try:
            messages = openai.beta.threads.messages.list(thread_id=self.thread_id)
            assistant_messages = [m for m in messages.data if m.role == "assistant"]

            if not assistant_messages:
                self.append_chat("❌ Assistant gave no response.")
                return

            last_msg = assistant_messages[0].content[0].text.value.strip()
            self.last_question = last_msg

            if "true" in last_msg.lower() or "filled_form" in last_msg.lower():
                with open("filled_form.json", "w") as f:
                    json.dump(self.responses, f, indent=2)
                self.append_chat("✅ Saved to filled_form.json")
                try:
                    agentops.end_session("Success")
                except:
                    pass
                return

            self.append_chat(f"🤖 Assistant: {last_msg}")
            self.hide_loading()
        except Exception as e:
            self.append_chat(f"❌ Error getting assistant response: {e}")
            try:
                agentops.end_session("Fail")
            except:
                pass

    def append_chat(self, msg):
        self.chat_log.config(state="normal")
        self.chat_log.insert(tk.END, msg + "\n\n")
        self.chat_log.config(state="disabled")
        self.chat_log.yview(tk.END)

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ChatApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Fatal error: {e}")
        try:
            agentops.end_session("Fail")
        except:
            pass
