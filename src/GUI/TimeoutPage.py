import customtkinter as ctk

# =====================================================
# PAGE 6: SESSION TIMEOUT
# =====================================================

class SessionTimeoutPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        self.configure(fg_color="#1a1a2e")

        ctk.CTkLabel(
            self,
            text="Session Timed Out",
            font=("Arial", 60, "bold"),
            text_color="#e0e0e0"
        ).place(relx=0.5, rely=0.42, anchor="center")

        ctk.CTkLabel(
            self,
            text="Returning to start screen..",
            font=("Arial", 26, "italic"),
            text_color="#888888"
        ).place(relx=0.5, rely=0.62, anchor="center")