# ResearchDraft – Minimal Ollama + Gradio App

ResearchDraft is a **local web interface** for turning research papers into
publication‑ready abstracts. It uses:

- an **Ollama model** (`researchdraft-lfm2`) defined by `Modelfile-lfm2`, and  
- a **Gradio chat UI** that accepts either **PDF uploads** or **pasted text**.

This `minimal_app` folder contains only the pieces you need to create a clean
GitHub repository and run the app.

---

## 1. What this project does

- **Input**: a research paper as a PDF or plain text.
- **Output**: a single‑paragraph, publication‑style abstract following a fixed
  structure (context, objective, methodology, key findings, significance).
- **Interface**: a chat‑like page where you can:
  - upload a PDF,
  - type questions or “Please generate an abstract for this paper”, and
  - see the model’s responses in a conversation view.

All abstract‑writing behavior is controlled by the system prompt inside
`Modelfile-lfm2`.

---

## 2. Files in this minimal app

- `Modelfile-lfm2`  
  Ollama model definition for `researchdraft-lfm2`. It:
  - points to the base `LFM2.5-1.2B` model, and  
  - sets a detailed system prompt that forces the model to write structured,
    single‑paragraph abstracts in formal academic style.

- `interface/gradio_ollama.py`  
  Minimal Gradio app that:
  - exposes a chat UI,
  - lets users upload PDFs or paste text,
  - calls the `researchdraft-lfm2` model via the Ollama HTTP API, and
  - shows the model’s responses in a chat window.

- `requirements.txt`  
  Python dependencies required to run the Gradio interface.

---

## 3. Prerequisites

1. **Python** 3.9+ (virtual environment recommended).
2. **Ollama** installed and running on your machine.  
   See the official instructions for your platform.
3. Sufficient disk and RAM to run the `LFM2.5-1.2B` model.

---

## 4. Setup

From inside the `RD` folder:

```bash
cd RD
# (Optional but recommended) create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # on macOS / Linux
# .venv\Scripts\activate         # on Windows PowerShell

# Install dependencies
pip install -r requirements.txt
```

---

## 5. Create the Ollama model

1. Make sure the Ollama server is running:

```bash
ollama serve
```

2. In another terminal (still inside `minimal_app`), create the model:

```bash
ollama create researchdraft -f Modelfile-lfm2
```

This registers a local Ollama model named **`researchdraft-lfm2`**, which the
Gradio app will call.

---

## 6. Run the Gradio interface

From the `RD` folder:

```bash
python interface/gradio_ollama.py
```

Gradio will print a local URL, typically something like:

```text
http://127.0.0.1:7860
```

Open that URL in your browser.

---

## 7. Using the app

1. **Upload a PDF (optional)**  
   - Click the `+ Upload PDF` button and select your research paper.  
   - The backend will extract text from the PDF using PyMuPDF (`pymupdf`).

2. **Ask for an abstract**  
   - In the message box, type something like:
     - `Please generate a technical abstract for this paper.`
   - Press **Enter** or click the arrow **➤** button.

3. **Read the response**  
   - The model’s answer appears in the `Conversation` panel.
   - You can continue asking follow‑up questions about the same paper.

4. **Without PDFs**  
   - If you prefer, paste the paper’s text directly into the message box and
     ask for an abstract; the app will use that text instead of a PDF.

---

## 8. Customization ideas

- **Change the base model** in `Modelfile-lfm2` (e.g., a different LFM2.5
  quantization or another GGUF model that works well for summarization).
- **Adjust sampling parameters** (temperature, top‑p, repeat penalty) in
  `Modelfile-lfm2` or in the `payload["options"]` inside
  `interface/gradio_ollama.py`.
- **Tweak the UI**:
  - change the title/description text,
  - alter the max token slider range,
  - customize colors via Gradio’s themes if desired.

This folder is intentionally small and self‑contained so you can push it as a
GitHub repository and share an easy, reproducible abstract‑generation app.

