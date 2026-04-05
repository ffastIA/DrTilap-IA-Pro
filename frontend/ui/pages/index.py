import reflex as rx
from ui.styles import HERO_BG_STYLE, WHITE, BUTTON_ACCENT

def index() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("Dr. Tilápia 2.0", color=WHITE, size="9"),
            rx.button("Entrar no Sistema", on_click=rx.redirect("/login"), **BUTTON_ACCENT),
            align="center",
            spacing="6",
            padding="2em",
        ),
        style=HERO_BG_STYLE,
        height="100vh",
        width="100%",
    )