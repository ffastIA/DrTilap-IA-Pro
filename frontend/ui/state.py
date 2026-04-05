import reflex as rx
import httpx


class State(rx.State):
    access_token: str = rx.LocalStorage("")
    user_role: str = rx.LocalStorage("")
    user_email: str = ""
    password: str = ""
    user_name: str = "Usuário"
    is_authenticated: bool = False
    files_to_upload: list[str] = []
    upload_status: str = ""
    reindex_status: str = ""
    is_loading: bool = False

    def check_login(self):
        if not self.access_token:
            return rx.redirect("/login")

    async def handle_login(self):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8080/auth/login",
                json={"email": self.user_email, "password": self.password}
            )
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.user_role = data.get("role")
                self.is_authenticated = True
                return rx.redirect("/hub")
            else:
                self.upload_status = "Erro no login"

    def logout(self):
        self.access_token = ""
        self.user_role = ""
        self.is_authenticated = False
        return rx.redirect("/login")

    async def handle_upload(self, files: list[rx.UploadFile]):
        self.is_loading = True
        async with httpx.AsyncClient() as client:
            for file in files:
                response = await client.post(
                    "http://localhost:8080/admin/upload",
                    files={"file": (file.filename, file.file, file.content_type)},
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                if response.status_code == 200:
                    self.upload_status = "Upload bem-sucedido"
                else:
                    self.upload_status = "Erro no upload"
        self.is_loading = False

    async def reindex_vectorstore(self):
        self.is_loading = True
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8080/admin/reindex",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            if response.status_code == 200:
                self.reindex_status = "Reindexação bem-sucedida"
            else:
                self.reindex_status = "Erro na reindexação"
        self.is_loading = False