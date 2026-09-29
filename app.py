import tkinter as tk
from tkinter import scrolledtext
import threading
import queue
import contextlib
import io
import main


class MyAssistantApp:
    def __init__(self, root):
        self.root = root

        root.title("MyAssistant")
        root.geometry("900x600")
        root.minsize(700, 500)

        self.output_queue = queue.Queue()

        # Main layout
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(0, weight=1)

        # Header
        header = tk.Frame(root, padx=20, pady=15)
        header.grid(row=0, column=0, sticky="ew")

        title = tk.Label(
            header,
            text="MY ASSISTANT",
            font=("Segoe UI", 22, "bold")
        )
        title.pack(anchor="w")

        status = tk.Label(
            header,
            text="Local AI Assistant • Ready",
            font=("Segoe UI", 10)
        )
        status.pack(anchor="w")

        # Conversation area
        self.output = scrolledtext.ScrolledText(
            root,
            wrap=tk.WORD,
            font=("Segoe UI", 11)
        )

        self.output.grid(
            row=1,
            column=0,
            padx=20,
            pady=(0, 10),
            sticky="nsew"
        )

        self.output.configure(state="disabled")

        # Input area
        input_frame = tk.Frame(root, padx=20, pady=10)
        input_frame.grid(
            row=2,
            column=0,
            sticky="ew"
        )

        input_frame.grid_columnconfigure(0, weight=1)

        self.entry = tk.Entry(
            input_frame,
            font=("Segoe UI", 12)
        )

        self.entry.grid(
            row=0,
            column=0,
            sticky="ew",
            ipady=8
        )

        self.send_button = tk.Button(
            input_frame,
            text="Send",
            font=("Segoe UI", 11, "bold"),
            width=10,
            command=self.send_command
        )

        self.send_button.grid(
            row=0,
            column=1,
            padx=(10, 0)
        )

        self.entry.bind(
            "<Return>",
            lambda event: self.send_command()
        )

        self.write_output(
            "MyAssistant is ready.\n"
            "Type a command below.\n\n"
        )

        self.entry.focus()

        root.after(100, self.check_output_queue)

    def write_output(self, text):
        self.output.configure(state="normal")
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.configure(state="disabled")

    def send_command(self):
        command = self.entry.get().strip()

        if not command:
            return

        self.entry.delete(0, tk.END)

        self.write_output(f"You: {command}\n")

        self.send_button.configure(state="disabled")
        self.entry.configure(state="disabled")

        thread = threading.Thread(
            target=self.process_command,
            args=(command,),
            daemon=True
        )

        thread.start()

    def process_command(self, command):
        captured = io.StringIO()

        try:
            with contextlib.redirect_stdout(captured):
                result = main.process_command(command)

            output = captured.getvalue()

            if output:
                self.output_queue.put(output)

            if result == "exit":
                self.output_queue.put("__EXIT__")

        except Exception as error:
            self.output_queue.put(
                f"Assistant: Error: {error}\n"
            )

        finally:
            self.output_queue.put("__READY__")

    def check_output_queue(self):
        try:
            while True:
                message = self.output_queue.get_nowait()

                if message == "__READY__":
                    self.send_button.configure(state="normal")
                    self.entry.configure(state="normal")
                    self.entry.focus()

                elif message == "__EXIT__":
                    self.root.after(
                        300,
                        self.root.destroy
                    )

                else:
                    self.write_output(message)

        except queue.Empty:
            pass

        self.root.after(
            100,
            self.check_output_queue
        )


def main_app():
    root = tk.Tk()
    MyAssistantApp(root)
    root.mainloop()


if __name__ == "__main__":
    main_app()