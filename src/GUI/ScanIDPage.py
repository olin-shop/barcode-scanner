import customtkinter as ctk
from PIL import Image

# =====================================================
# PAGE 1: SCAN ID
# =====================================================

class ScanIDPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        dark_green  = "#2E7D32"
        light_green = "#81C784"
        self.configure(fg_color=dark_green)

        img = Image.open("green_corner.png")
        self.corner_tl = ctk.CTkImage(light_image=img,                          dark_image=img,                          size=(90, 90))
        self.corner_tr = ctk.CTkImage(light_image=img.rotate(270, expand=True), dark_image=img.rotate(270, expand=True), size=(90, 90))
        self.corner_bl = ctk.CTkImage(light_image=img.rotate(90,  expand=True), dark_image=img.rotate(90,  expand=True), size=(90, 90))
        self.corner_br = ctk.CTkImage(light_image=img.rotate(180, expand=True), dark_image=img.rotate(180, expand=True), size=(80, 80))

        ctk.CTkLabel(self, image=self.corner_tl, text="").place(relx=.2, rely=.2, anchor="center")
        ctk.CTkLabel(self, image=self.corner_tr, text="").place(relx=.8, rely=.2, anchor="center")
        ctk.CTkLabel(self, image=self.corner_bl, text="").place(relx=.2, rely=.8, anchor="center")
        ctk.CTkLabel(self, image=self.corner_br, text="").place(relx=.8, rely=.8, anchor="center")

        ctk.CTkLabel(
            self,
            text="SCAN ID",
            font=("Arial", 88, "bold"),
            text_color="white"
        ).place(relx=0.5, rely=0.5, anchor="center")
