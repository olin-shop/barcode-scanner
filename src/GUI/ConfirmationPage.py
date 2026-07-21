import customtkinter as ctk

# =====================================================
# PAGE 5: FINAL CONFIRMATION
# =====================================================

class FinalConfirmationPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        ctk.CTkLabel(
            self,
            text="Confirmed",
            font=("Arial", 80, "bold")
        ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            self,
            text="Closing session..",
            font=("Arial", 30, "italic")
        ).place(relx=0.5, rely=0.7, anchor="center")