"""
ResearchDraft — Ollama Interface
=================================
Web UI for generating research paper abstracts using an Ollama backend.
Supports both PDF file uploads and pasted text.

Usage:
    1. Ensure Ollama is running (`ollama serve`)
    2. Create your model: `ollama create researchdraft-lfm2 -f Modelfile-lfm2`
    3. Install dependencies: `pip install gradio requests pymupdf`
    4. Run this script: `python interface/gradio_ollama.py`
"""

import gradio as gr

try:
    import requests
except Exception as e:
    requests = None
    _REQUESTS_IMPORT_ERROR = e

try:
    import fitz  # PyMuPDF
except Exception as e:
    fitz = None
    _FITZ_IMPORT_ERROR = e

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OLLAMA_MODEL_NAME = "researchdraft-lfm2"
OLLAMA_API_URL = "http://localhost:11434/api/generate"


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file using PyMuPDF."""
    if fitz is None:
        return (
            "PyMuPDF (`pymupdf`) is not available in this Python environment.\n"
            f"Import error: {_FITZ_IMPORT_ERROR}"
        )
    try:
        doc = fitz.open(pdf_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts).strip()
    except Exception as e:
        return f"Error reading PDF: {e}"


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------
def generate_abstract(
    pdf_file,
    paper_text: str,
    max_tokens: int = 512,
    temperature: float = 0.3,
) -> str:
    """Generate an abstract using the Ollama API.

    Accepts either a PDF upload or pasted text. If both are provided,
    the PDF takes priority.
    """
    # --- Resolve input text ---
    if pdf_file:
        # `pdf_file` may be:
        # - a single path string
        # - a file-like object
        # - a list from an UploadButton (take the first)
        if isinstance(pdf_file, list):
            pdf_file = pdf_file[0] if pdf_file else None

        # Gradio `type="filepath"` returns a string path.
        pdf_path = pdf_file if isinstance(pdf_file, str) else getattr(pdf_file, "name", None)
        if not pdf_path:
            return "❌ Could not read the uploaded PDF file path."

        extracted = extract_text_from_pdf(pdf_path)
        if extracted.startswith("Error reading PDF"):
            return f"\u274c {extracted}"
        paper_text = extracted

    if not paper_text or not paper_text.strip():
        return "\u26a0\ufe0f Please upload a PDF or paste research paper text."

    # Truncate to keep the prompt within context window
    excerpt = paper_text[:3000].strip()
    if len(paper_text) > 3000:
        excerpt += "\n[... remaining text truncated for context length ...]"

    prompt = (
        "Below is the content of a research paper. "
        "Generate a publication-ready first draft of the abstract.\n\n"
        f"### Research Paper Content:\n{excerpt}"
    )

    payload = {
        "model": OLLAMA_MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "repeat_penalty": 1.15,
        },
    }

    if requests is None:
        return (
            "The HTTP client library `requests` is not available in this Python "
            f"environment. Import error: {_REQUESTS_IMPORT_ERROR}"
        )

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "Error: No response text from Ollama.")
    except requests.ConnectionError:
        return (
            "Cannot connect to the Ollama server.\n"
            "Make sure Ollama is running (`ollama serve`) and reachable at "
            f"{OLLAMA_API_URL}."
        )
    except Exception as e:
        return f"Error while calling Ollama: {e}"


def chat_respond(
    message: str,
    history,
    pdf_file,
    max_tokens: int,
    temperature: float,
):
    """Chat-style wrapper around `generate_abstract`.

    Each user message is treated as the paper text (or instructions) and optionally
    combined with an uploaded PDF, but the model itself is called in a single-turn
    fashion for robustness.
    """
    if not (message and message.strip()) and not pdf_file:
        history = history + [
            (
                "",
                "Please upload a PDF or enter some text about your research paper.",
            )
        ]
        return history, ""

    reply = generate_abstract(
        pdf_file=pdf_file,
        paper_text=message or "",
        max_tokens=max_tokens,
        temperature=temperature,
    )
    history = history + [(message, reply)]
    return history, ""


# ---------------------------------------------------------------------------
# Helpers for rendering past conversations
# ---------------------------------------------------------------------------
def _get_conversation_titles(conversations):
    return [c["title"] for c in conversations]


def _render_conversation_list(conversations):
    """Render a simple markdown list of past conversation titles."""
    titles = _get_conversation_titles(conversations)
    if not titles:
        return "**Past conversations**\n\n_None yet._"
    lines = [f"- {title}" for title in titles]
    return "**Past conversations**\n\n" + "\n".join(lines)


def _clear_chat(chat_history, conversations):
    """Store the finished chat as a 'past conversation' and clear the current one."""
    # chat_history is a list of (user, assistant) tuples
    if chat_history:
        # Use the first non-empty user message as the title
        first_user = ""
        for user_msg, _assistant_msg in chat_history:
            if user_msg:
                first_user = user_msg.strip()
                break
        title = first_user or "Untitled conversation"
        if len(title) > 60:
            title = title[:57] + "..."
        conversations = conversations + [{"title": title, "history": chat_history}]

    titles = _get_conversation_titles(conversations)
    dropdown_update = gr.Dropdown(choices=titles, value=None)
    return conversations, _render_conversation_list(conversations), dropdown_update, [], ""


def _rename_conversation(selected_title, new_title, conversations):
    """Rename a stored past conversation."""
    if not selected_title or not new_title or not new_title.strip():
        # Nothing to do; just re-render with existing state
        titles = _get_conversation_titles(conversations)
        dropdown_update = gr.Dropdown(choices=titles, value=selected_title or None)
        return conversations, _render_conversation_list(conversations), dropdown_update

    new_title = new_title.strip()
    for conv in conversations:
        if conv["title"] == selected_title:
            conv["title"] = new_title
            break

    titles = _get_conversation_titles(conversations)
    dropdown_update = gr.Dropdown(choices=titles, value=new_title)
    return conversations, _render_conversation_list(conversations), dropdown_update


def _load_conversation(selected_title, conversations):
    """Load a past conversation into the chat window."""
    if not selected_title:
        return []
    for conv in conversations:
        if conv["title"] == selected_title:
            return conv["history"]
    return []


# ---------------------------------------------------------------------------
# Gradio UI (chat-style, with a sidebar listing past conversations)
# ---------------------------------------------------------------------------
with gr.Blocks(title="ResearchDraft: Abstract Chat") as demo:
    gr.Markdown(
        "## ResearchDraft: Abstract Assistant\n"
        "Upload a research paper PDF (optional) and chat with the model to generate "
        "publication-ready abstracts or discuss the paper."
    )

    with gr.Row():
        # Left sidebar: past conversations and PDF / settings
        with gr.Column(scale=1):
            conversations_state = gr.State([])
            conversations_md = gr.Markdown(_render_conversation_list([]))
            conversations_dropdown = gr.Dropdown(
                label="Open past conversation",
                choices=[],
                interactive=True,
            )

            new_chat_btn = gr.Button("New Chat")

            rename_box = gr.Textbox(
                label="Rename selected chat",
                placeholder="Enter new title...",
                lines=1,
            )
            rename_btn = gr.Button("Rename")

            # Small "+" style upload button instead of a large file box
            pdf_input = gr.UploadButton(
                "+ Upload PDF",
                file_types=[".pdf"],
                type="filepath",
            )
            with gr.Row():
                max_tokens_slider = gr.Slider(
                    minimum=128,
                    maximum=1024,
                    value=512,
                    step=64,
                    label="Max Length (tokens)",
                )
                temp_slider = gr.Slider(
                    minimum=0.1,
                    maximum=1.0,
                    value=0.3,
                    step=0.1,
                    label="Temperature",
                )

        # Main chat area
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(label="Conversation", height=400)
            with gr.Row():
                msg = gr.Textbox(
                    label="Message",
                    placeholder="Ask for an abstract or query about your paper...",
                    lines=3,
                    show_label=False,
                    scale=10,
                )
                # Tiny arrow-style send button
                send_btn = gr.Button("➤", variant="primary", scale=1)

    # Submit on Enter and on Send button click
    msg.submit(
        fn=chat_respond,
        inputs=[msg, chatbot, pdf_input, max_tokens_slider, temp_slider],
        outputs=[chatbot, msg],
    )
    send_btn.click(
        fn=chat_respond,
        inputs=[msg, chatbot, pdf_input, max_tokens_slider, temp_slider],
        outputs=[chatbot, msg],
    )
    new_chat_btn.click(
        fn=_clear_chat,
        inputs=[chatbot, conversations_state],
        outputs=[conversations_state, conversations_md, conversations_dropdown, chatbot, msg],
    )

    rename_btn.click(
        fn=_rename_conversation,
        inputs=[conversations_dropdown, rename_box, conversations_state],
        outputs=[conversations_state, conversations_md, conversations_dropdown],
    )

    conversations_dropdown.change(
        fn=_load_conversation,
        inputs=[conversations_dropdown, conversations_state],
        outputs=chatbot,
    )

if __name__ == "__main__":
    print(f"Starting ResearchDraft with model: {OLLAMA_MODEL_NAME}")
    # Use share=True so the app still works even if localhost
    # is blocked or not directly accessible on this system.
    demo.launch(share=True)
