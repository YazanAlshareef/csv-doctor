"""Gradio demo for csv-doctor. Run: python app.py"""
import gradio as gr

import web_helpers as wh


def show(o: wh.Outcome):
    ok = o.cleaned_path is not None
    return (
        o.status,
        o.profile_md,
        o.preview,
        o.log_preview,
        gr.DownloadButton(value=o.cleaned_path, interactive=ok),
        gr.DownloadButton(value=o.log_path, interactive=ok),
    )


def on_run(path, dayfirst):
    return show(wh.run(path, dayfirst))


def on_sample(dayfirst):
    return show(wh.run_sample(dayfirst))


with gr.Blocks(title="csv-doctor") as demo:
    gr.Markdown(
        "# csv-doctor\n"
        f"Profile and clean a messy CSV. Limits: {wh.MAX_BYTES // 2**20} MB and {wh.MAX_ROWS:,} rows. "
        "Nothing is stored: files are processed in memory and the downloads sit in a temporary folder."
    )
    with gr.Row():
        with gr.Column():
            upload = gr.File(label="CSV file", file_types=[".csv"], type="filepath")
            dayfirst = gr.Checkbox(label="Read ambiguous dates like 03/04/2024 day first", value=True)
            with gr.Row():
                run_btn = gr.Button("Profile and clean", variant="primary")
                sample_btn = gr.Button("Load sample CSV")
            status = gr.Textbox(label="Status", interactive=False)
        with gr.Column():
            dl_clean = gr.DownloadButton("Download cleaned CSV", interactive=False)
            dl_log = gr.DownloadButton("Download change log", interactive=False)
    with gr.Tab("Profile report"):
        report = gr.Markdown(label="Profile report")
    with gr.Tab("Cleaned preview"):
        preview = gr.Dataframe(label="Cleaned preview", interactive=False, wrap=True)
    with gr.Tab("Change log"):
        log = gr.Dataframe(label="Change log", interactive=False, wrap=True)

    outs = [status, report, preview, log, dl_clean, dl_log]
    run_btn.click(on_run, [upload, dayfirst], outs)
    sample_btn.click(on_sample, [dayfirst], outs)

if __name__ == "__main__":
    demo.launch()
