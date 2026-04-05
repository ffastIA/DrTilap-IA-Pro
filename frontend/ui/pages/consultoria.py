import reflex as rx
from ui.state import State
from ui.styles import GLASS_CONTAINER_STYLE, ACCENT, WHITE, BACKGROUND_GRADIENT

def message_box(chat_pair):
    return rx.vstack(
        rx.box(rx.text(chat_pair[0], color=WHITE), align_self="flex-end", bg="rgba(255,255,255,0.1)", padding="1em", border_radius="1em"),
        rx.box(rx.markdown(chat_pair[1]), align_self="flex-start", bg="rgba(0,206,209,0.1)", padding="1em", border_radius="1em", border=f"1px solid {ACCENT}33"),
        width="100%", spacing="2"
    )

def consultoria() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.hstack(
                rx.icon(tag="bot", color=ACCENT),
                rx.heading("Consultor IA", color=WHITE),
                rx.spacer(),
                rx.link("Voltar", href="/hub", color=WHITE),
                width="100%", align="center"
            ),
            rx.scroll_area(
                rx.vstack(rx.foreach(State.chat_history, message_box), width="100%", spacing="4"),
                height="60vh", width="100%"
            ),
            rx.hstack(
                rx.input(placeholder="Sua dúvida...", value=State.current_message, on_change=State.set_current_message, width="100%", color=WHITE),
                rx.button(rx.icon(tag="send"), on_click=State.handle_chat, is_loading=State.is_loading, bg=ACCENT),
                width="100%"
            ),
            width="800px", padding="2em", **GLASS_CONTAINER_STYLE
        ),
        height="100vh", width="100%", background=BACKGROUND_GRADIENT
    )