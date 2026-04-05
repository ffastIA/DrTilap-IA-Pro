# frontend/ui/styles.py
# Paleta de cores
PRIMARY = "#004e92"
ACCENT = "#ff6b6b"
SECONDARY = "#4ecdc4"
WHITE = "#ffffff"
TEXT_MUTED = "#b0b0b0"

# Gradiente de fundo
BACKGROUND_GRADIENT = "linear-gradient(135deg, #004e92 0%, #000000 100%)"

# Estilo do fundo do herói
HERO_BG_STYLE = {
    "background_image": "url('/hub01.jpeg')",
    "background_size": "cover",
    "background_position": "center",
    "background_repeat": "no-repeat",
    "background_attachment": "fixed",
}

# Estilo do container de vidro
GLASS_CONTAINER_STYLE = {
    "background_color": "rgba(255, 255, 255, 0.12)",
    "backdrop_filter": "blur(12px)",
    "border_radius": "12px",
    "padding": "20px",
    "box_shadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
}

# Estilo de input
INPUT_STYLE = {
    "background_color": "rgba(0, 0, 0, 0.7)",
    "color": WHITE,
    "border": f"1px solid {ACCENT}",
    "border_radius": "8px",
    "padding": "10px",
    "font_size": "16px",
    "_focus": {
        "border_color": PRIMARY,
        "box_shadow": f"0 0 0 1px {PRIMARY}",
    },
}

# Estilo do botão de destaque
BUTTON_ACCENT = {
    "background_color": ACCENT,
    "color": WHITE,
    "border_radius": "8px",
    "padding": "12px 24px",
    "font_size": "16px",
    "font_weight": "bold",
    "cursor": "pointer",
    "transition": "all 0.3s ease",
    "_hover": {
        "background_color": "#ff5252",
        "transform": "translateY(-2px)",
        "box_shadow": "0 4px 8px rgba(255, 107, 107, 0.3)",
    },
}