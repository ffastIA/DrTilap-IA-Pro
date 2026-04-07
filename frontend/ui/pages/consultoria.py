import reflex as rx
from ..state import State
from ..styles import PRIMARY, ACCENT, SECONDARY


def message_box(chat: list) -> rx.Component:
    """Renderiza uma bolha de mensagem individual."""
    return rx.vstack(
        # Pergunta do Usuário
        rx.box(
            rx.text(chat[0], color="white", font_weight="500"),
            background="rgba(255, 255, 255, 0.1)",
            backdrop_filter="blur(10px)",
            border=f"1px solid rgba(255, 255, 255, 0.2)",
            padding="1rem",
            border_radius="15px 15px 0px 15px",
            align_self="flex-end",
            max_width="80%",
        ),
        # Resposta da IA
        rx.box(
            rx.vstack(
                rx.text(chat[1], color="white"),
                rx.cond(
                    chat[1] != "Pensando...",
                    rx.hstack(
                        rx.icon(tag="info", size=14, color=SECONDARY),
                        rx.text("Baseado em manuais técnicos", font_size="0.7rem", color=SECONDARY),
                        margin_top="0.5rem",
                    ),
                ),
                align_items="start",
            ),
            background=f"linear-gradient(135deg, {PRIMARY}88, #00000088)",
            backdrop_filter="blur(12px)",
            border=f"1px solid {SECONDARY}44",
            padding="1rem",
            border_radius="15px 15px 15px 0px",
            align_self="flex-start",
            max_width="85%",
            margin_top="0.5rem",
        ),
        width="100%",
        spacing="1",
    )


def consultoria() -> rx.Component:
    return rx.center(
        # Background Imersivo
        rx.box(
            position="fixed",
            top="0",
            left="0",
            width="100%",
            height="100%",
            background="url('/bg_hero.png')",
            background_size="cover",
            background_position="center",
            filter="brightness(0.4) blur(8px)",
            z_index="-1",
        ),

        rx.vstack(
            # Header da Página
            rx.hstack(
                rx.image(src="/favicon.ico", width="40px", height="auto"),
                rx.heading("Consultor Dr. Tilápia", size="7", color="white"),
                rx.spacer(),
                rx.badge("RAG Ativo", color_scheme="cyan", variant="outline"),
                width="100%",
                padding_bottom="2rem",
            ),

            # Área de Chat (Scrollable)
            rx.scroll_area(
                rx.vstack(
                    rx.foreach(State.chat_history, message_box),
                    width="100%",
                    spacing="4",
                    padding="1rem",
                ),
                height="60vh",
                width="100%",
                background="rgba(0, 0, 0, 0.3)",
                border_radius="20px",
                border="1px solid rgba(255, 255, 255, 0.1)",
                margin_bottom="1.5rem",
            ),

            # Área de Input
            rx.hstack(
                rx.input(
                    placeholder="Digite sua dúvida técnica (ex: Qual a temperatura ideal?)...",
                    value=State.current_message,
                    on_change=State.set_current_message,
                    on_key_down=lambda e: rx.cond(e.key == "Enter", State.answer),
                    background="rgba(255, 255, 255, 0.05)",
                    border=f"1px solid rgba(255, 255, 255, 0.2)",
                    color="white",
                    _focus={"border": f"1px solid {SECONDARY}"},
                    height="3.5rem",
                    flex_grow="1",
                    border_radius="12px",
                ),
                rx.button(
                    rx.cond(
                        State.is_loading,
                        rx.spinner(size="2"),
                        rx.icon(tag="send"),
                    ),
                    on_click=State.answer,
                    background=f"linear-gradient(45deg, {PRIMARY}, {SECONDARY})",
                    color="white",
                    _hover={"transform": "scale(1.05)", "opacity": "0.9"},
                    height="3.5rem",
                    width="4rem",
                    border_radius="12px",
                    is_disabled=State.is_loading,
                ),
                width="100%",
                spacing="3",
            ),

            # Rodapé informativo
            rx.text(
                "O Dr. Tilápia utiliza IA para analisar manuais. Sempre valide com um técnico local.",
                font_size="0.7rem",
                color="rgba(255, 255, 255, 0.5)",
                margin_top="1rem",
            ),

            width="100%",
            max_width="900px",
            padding="2rem",
            background="rgba(255, 255, 255, 0.02)",
            backdrop_filter="blur(20px)",
            border_radius="30px",
            border="1px solid rgba(255, 255, 255, 0.1)",
            box_shadow="0 8px 32px 0 rgba(0, 0, 0, 0.8)",
        ),
        width="100%",
        min_height="100vh",
        padding_y="2rem",
    )