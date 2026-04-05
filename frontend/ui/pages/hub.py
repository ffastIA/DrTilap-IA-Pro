import reflex as rx
from ui.state import State
from ui.styles import WHITE, ACCENT, GLASS_CONTAINER_STYLE


def floating_card(title: str, desc: str, href: str, icon: str, **kwargs):
    return rx.link(
        rx.vstack(
            rx.icon(tag=icon, size=30, color=ACCENT),
            rx.text(title, font_weight="bold", color=WHITE),
            rx.text(desc, font_size="0.8em", color="rgba(255,255,255,0.6)"),
            spacing="2", align="center",
        ),
        href=href, padding="1.5em", **GLASS_CONTAINER_STYLE, position="absolute", **kwargs
    )


def hub() -> rx.Component:
    return rx.box(
        rx.image(src="/hub01.jpeg", width="100%", height="100vh", object_fit="cover", position="absolute", z_index="-1",
                 filter="brightness(0.4)"),
        rx.center(rx.heading(f"Olá, {State.user_name}", size="8", color=WHITE, position="absolute", top="10%")),

        floating_card("Consultoria", "Chat IA", "/consultoria", "message-square", top="40%", left="15%"),
        floating_card("Dashboard", "Métricas", "/dashboard", "bar-chart-3", top="40%", right="15%"),

        rx.cond(
            State.user_role == "admin",
            floating_card("Admin RAG", "Gestão", "/admin-rag", "database", bottom="15%", left="43%"),
        ),

        rx.button("Sair", on_click=State.logout, position="absolute", top="2em", right="2em", variant="ghost",
                  color=WHITE),
        height="100vh", width="100%", position="relative"
    )