import reflex as rx
from ui.styles import GLASS_CONTAINER_STYLE, ACCENT, WHITE, BACKGROUND_GRADIENT, SECONDARY

def metric(label, val, unit):
    return rx.vstack(
        rx.text(label, font_size="0.8em", color="rgba(255,255,255,0.6)"),
        rx.hstack(rx.text(val, font_size="2em", font_weight="bold", color=WHITE), rx.text(unit, color=SECONDARY)),
        bg="rgba(0,0,0,0.2)", padding="1.5em", border_radius="1em", width="180px"
    )

def dashboard() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("Métricas em Tempo Real", color=WHITE),
            rx.flex(
                metric("Temperatura", "26.5", "°C"),
                metric("Oxigênio", "7.2", "mg/L"),
                metric("pH", "6.8", "pH"),
                gap="1.5em", flex_wrap="wrap", justify="center"
            ),
            rx.link("Voltar ao Hub", href="/hub", color=WHITE, margin_top="2em"),
            width="800px", padding="3em", **GLASS_CONTAINER_STYLE
        ),
        height="100vh", width="100%", background=BACKGROUND_GRADIENT
    )