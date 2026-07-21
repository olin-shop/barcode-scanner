import customtkinter as ctk

# =====================================================
# PAGE 6: Loading inbetween screens
# =====================================================

class LoadingPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        self.configure(fg_color="#1a1a2e")

        ctk.CTkLabel(
            self,
            text="Loading...",
            font=("Arial", 60, "bold"),
            text_color="#e0e0e0"
        ).place(relx=0.5, rely=0.42, anchor="center")