import customtkinter as ctk

#from ScanIDPage import ScanIDPage
from TimeoutPage import SessionTimeoutPage
from ConfirmationPage import FinalConfirmationPage
from LoadingPage import LoadingPage
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.geometry("800x480")
        self.title("Barcode System")

        # Uncomment on Raspberry Pi
        # self.attributes("-fullscreen", True)

        self.frames = {}

        for F in (
            #ScanIDPage,
            FinalConfirmationPage,
            SessionTimeoutPage,
            LoadingPage,
        ):
            frame = F(self)
            self.frames[F.__name__] = frame

            frame.place(
                relx=0,
                rely=0,
                relwidth=1,
                relheight=1
            )

        self.show_frame("LoadingPage")

    def show_frame(self, page_name):
        self.frames[page_name].tkraise()
if __name__ == "__main__":
    app = App()    # Create instance
    app.mainloop()
