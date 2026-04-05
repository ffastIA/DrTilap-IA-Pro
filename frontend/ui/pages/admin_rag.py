from ui.state import State
from ui.styles import GLASS_CONTAINER_STYLE, ACCENT, WHITE, BACKGROUND_GRADIENT

import reflex as rx


def admin_rag() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading(
                "Administração do RAG - DrTilapIA 2.0",
                color=WHITE,
                size="lg",
            ),
            rx.upload(
                rx.button(
                    "Selecionar PDFs",
                    color=WHITE,
                    bg=ACCENT,
                ),
                id="upload_pdfs",
                multiple=True,
                accept={".pdf": "application/pdf"},
            ),
            rx.button(
                "Fazer Upload",
                on_click=State.handle_upload(rx.upload_files(id="upload_pdfs")),
                color=WHITE,
                bg=ACCENT,
            ),
            rx.vstack(
                rx.text("Arquivos selecionados:", color=WHITE),
                rx.foreach(State.files_to_upload, lambda file: rx.text(file, color=WHITE)),
            ),
            rx.button(
                "Reindexar Base de Conhecimento",
                on_click=State.reindex_vectorstore,
                color=WHITE,
                bg=ACCENT,
            ),
            rx.cond(
                State.upload_status,
                rx.text(State.upload_status, color=WHITE),
            ),
            rx.cond(
                State.reindex_status,
                rx.text(State.reindex_status, color=WHITE),
            ),
            spacing="4",
            align="center",
        ),
        style={
            **GLASS_CONTAINER_STYLE,
            "bg": "rgba(0, 0, 0, 0.4)",
            "backdrop_filter": "blur(10px)",
        },
        height="100vh",
        width="100%",
        bg=BACKGROUND_GRADIENT,
    )