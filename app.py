import gradio as gr
from query import ask

def handle_query(question):
    if not question.strip():
        return "Please enter a question.", ""
    result = ask(question)
    sources = "\n".join(f"• {s}" for s in result["sources"])
    return result["answer"], sources

with gr.Blocks(title="Stevens CS Professor Guide") as demo:
    gr.Markdown("## Stevens CS Unofficial Professor Guide")
    gr.Markdown("Ask about CS professors at Stevens Institute of Technology.")

    inp = gr.Textbox(label="Your question", placeholder="e.g. What do students say about Prof. Terolli?")
    btn = gr.Button("Ask")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=3)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])

demo.launch()