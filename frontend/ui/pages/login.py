import reflex as rx
from ui.state import State
from ui.styles import WHITE, GLASS_CONTAINER_STYLE, BUTTON_ACCENT, PRIMARY

def login_page():
    return rx.center(
        rx.vstack(
            rx.heading("Dr. Tilápia 2.0", size="8", color=WHITE),
            rx.input(placeholder="E-mail", on_change=State.set_user_email, width="100%", bg="rgba(255,255,255,0.05)"),
            rx.input(placeholder="Senha", type="password", on_change=State.set_password, width="100%", bg="rgba(255,255,255,0.05)"),
            rx.button("Entrar", on_click=State.handle_login, is_loading=State.is_loading, width="100%", **BUTTON_ACCENT),
            rx.text(State.error_message, color="red"),
            spacing="4", padding="3em", width="400px", **GLASS_CONTAINER_STYLE
        ),
        height="100vh", width="100%", background=f"radial-gradient(circle, {PRIMARY}, #000)"
    )