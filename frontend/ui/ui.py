import reflex as rx
from ui.state import State
from ui.pages.index import index
from ui.pages.login import login_page
from ui.pages.hub import hub
# from ui.pages.consultoria import consultoria
# from ui.pages.admin_rag import admin_rag
# from ui.pages.dashboard import dashboard

app = rx.App(
    theme=rx.theme(appearance="dark", accent_color="blue")
)

# Registro de Rotas
app.add_page(index, route="/")
app.add_page(login_page, route="/login")
app.add_page(hub, route="/hub", on_load=State.check_login)
# app.add_page(consultoria, route="/consultoria", on_load=State.check_login)
# app.add_page(admin_rag, route="/admin-rag", on_load=State.check_login)
# app.add_page(dashboard, route="/dashboard", on_load=State.check_login)