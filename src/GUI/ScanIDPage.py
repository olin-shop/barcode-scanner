import customtkinter as ctk
from PIL import Image

from GUI import gui_constants as const

# =====================================================
# PAGE 1: SCAN ID
# =====================================================

class ScanIDPage(ctk.CTkFrame):
    """
    Initial page asking the user to scan their Olin ID.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame) -> None:
        super().__init__(master)

        self.configure(fg_color=const.BG_LIGHT_BLUE)

        # Central container card for clean Olin branding presentation
        card = ctk.CTkFrame(
            self,
            corner_radius=24,
            border_width=2,
            border_color=const.BORDER_BLUE,
            fg_color=const.BG_WHITE
        )
        card.place(relx=0.5, rely=0.5, relwidth=0.88, relheight=0.82, anchor="center")

        # Loaded via a path built from this file's location, so the app
        # doesn't care what directory it was launched from.
        self._corner_images: list[ctk.CTkImage] = []
        try:
            image_path = const.STATIC_DIR / "green_corner.png"
            img = Image.open(image_path)
            self.corner_tl = ctk.CTkImage(light_image=img,                          dark_image=img,                          size=(90, 90))
            self.corner_tr = ctk.CTkImage(light_image=img.rotate(270, expand=True), dark_image=img.rotate(270, expand=True), size=(90, 90))
            self.corner_bl = ctk.CTkImage(light_image=img.rotate(90,  expand=True), dark_image=img.rotate(90,  expand=True), size=(90, 90))
            self.corner_br = ctk.CTkImage(light_image=img.rotate(180, expand=True), dark_image=img.rotate(180, expand=True), size=(90, 90))

            self._corner_images = [self.corner_tl, self.corner_tr, self.corner_bl, self.corner_br]

            ctk.CTkLabel(card, image=self.corner_tl, text="").place(relx=.15, rely=.2, anchor="center")
            ctk.CTkLabel(card, image=self.corner_tr, text="").place(relx=.85, rely=.2, anchor="center")
            ctk.CTkLabel(card, image=self.corner_bl, text="").place(relx=.15, rely=.8, anchor="center")
            ctk.CTkLabel(card, image=self.corner_br, text="").place(relx=.85, rely=.8, anchor="center")
        except Exception:
            pass

        ctk.CTkLabel(
            card,
            text="SCAN ID",
            font=const.FONT_HUGE,
            text_color=const.OLIN_BLUE
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Pulsing visual animation state
        self._base_size: int = 85
        self._max_size: int = 98
        self._current_size: float = float(self._base_size)
        self._pulse_direction: int = 1  # +1 for growing, -1 for shrinking
        self._is_paused: bool = False
        
        if self._corner_images:
            self._animate_pulse()

    def _animate_pulse(self) -> None:
        """
        Animates the corner images by pulsing them smoothly (growing, shrinking, pausing, repeating).
        """
        try:
            if not self.winfo_exists():
                return

            if self._is_paused:
                self._is_paused = False
                self.after(500, self._animate_pulse)  # Pause at base size for 500ms
                return

            step = 0.8
            self._current_size += self._pulse_direction * step

            if self._current_size >= self._max_size:
                self._current_size = float(self._max_size)
                self._pulse_direction = -1
            elif self._current_size <= self._base_size:
                self._current_size = float(self._base_size)
                self._pulse_direction = 1
                self._is_paused = True  # Pause after completing full pulse cycle

            sz = int(self._current_size)
            for img in self._corner_images:
                img.configure(size=(sz, sz))

            # Schedule next frame in 30ms for 30+ FPS smooth animation
            delay = 500 if self._is_paused else 30
            self.after(delay, self._animate_pulse)
        except Exception:
            pass

