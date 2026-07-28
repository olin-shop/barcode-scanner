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
        try:
            image_path = const.STATIC_DIR / "olin_blue_corner.png"
            self._base_img = Image.open(image_path)
            self.corner_tl = ctk.CTkImage(light_image=self._base_img,                          dark_image=self._base_img,                          size=(90, 90))
            self.corner_tr = ctk.CTkImage(light_image=self._base_img.rotate(270, expand=True), dark_image=self._base_img.rotate(270, expand=True), size=(90, 90))
            self.corner_bl = ctk.CTkImage(light_image=self._base_img.rotate(90,  expand=True), dark_image=self._base_img.rotate(90,  expand=True), size=(90, 90))
            self.corner_br = ctk.CTkImage(light_image=self._base_img.rotate(180, expand=True), dark_image=self._base_img.rotate(180, expand=True), size=(90, 90))

            self.lbl_corner_tl = ctk.CTkLabel(card, image=self.corner_tl, text="")
            self.lbl_corner_tr = ctk.CTkLabel(card, image=self.corner_tr, text="")
            self.lbl_corner_bl = ctk.CTkLabel(card, image=self.corner_bl, text="")
            self.lbl_corner_br = ctk.CTkLabel(card, image=self.corner_br, text="")

            self.lbl_corner_tl.place(relx=.15, rely=.2, anchor="center")
            self.lbl_corner_tr.place(relx=.85, rely=.2, anchor="center")
            self.lbl_corner_bl.place(relx=.15, rely=.8, anchor="center")
            self.lbl_corner_br.place(relx=.85, rely=.8, anchor="center")
        except Exception:
            self._base_img = None
            self.lbl_corner_tl = None
            self.lbl_corner_tr = None
            self.lbl_corner_bl = None
            self.lbl_corner_br = None

        # SCAN ID Header centered
        self.scan_id_label = ctk.CTkLabel(
            card,
            text="SCAN ID",
            font=const.FONT_HUGE,
            text_color=const.OLIN_BLUE
        )
        self.scan_id_label.place(relx=0.5, rely=0.5, anchor="center")

        # Animated square dots INSIDE the central card in OLIN_PINK
        # Top-left corner: grows left to right
        self.tl_dots_frame = ctk.CTkFrame(card, fg_color=const.BG_WHITE)
        self.tl_dots_frame.place(relx=0.222, rely=0.092, anchor="nw")
        self.tl_dots = []
        for _ in range(5):
            dot = ctk.CTkFrame(self.tl_dots_frame, width=14, height=14, fg_color=const.BG_WHITE, corner_radius=0)
            dot.pack(side="left", padx=3)
            self.tl_dots.append(dot)

        # Bottom-right corner: grows right to left
        self.br_dots_frame = ctk.CTkFrame(card, fg_color=const.BG_WHITE)
        self.br_dots_frame.place(relx=0.778, rely=0.915, anchor="se")
        self.br_dots = []
        for _ in range(5):
            dot = ctk.CTkFrame(self.br_dots_frame, width=14, height=14, fg_color=const.BG_WHITE, corner_radius=0)
            dot.pack(side="left", padx=3)
            self.br_dots.append(dot)

        self._dots_count = 0
        self._dots_direction = 1
        self._is_confirming = False
        self._animate_dots()

    def update_scale(self, scale: float) -> None:
        """Dynamically scale fonts, images, and dots when screen size changes."""
        new_font_size = max(24, int(88 * scale))
        self.scan_id_label.configure(font=(const.FONT_FAMILY, new_font_size, "bold"))

        if hasattr(self, "_base_img") and self._base_img:
            img_size = max(30, int(90 * scale))
            self.corner_tl.configure(size=(img_size, img_size))
            self.corner_tr.configure(size=(img_size, img_size))
            self.corner_bl.configure(size=(img_size, img_size))
            self.corner_br.configure(size=(img_size, img_size))

        dot_size = max(6, int(14 * scale))
        for dot in self.tl_dots + self.br_dots:
            dot.configure(width=dot_size, height=dot_size)

    def trigger_confirm_animation(self, on_complete: callable = None) -> None:
        """
        Erase pink dots and animate four corners moving in and out like a confirmation click.
        Executes on_complete callback when finished.
        """
        if self._is_confirming:
            return
        self._is_confirming = True

        # Erase pink dots
        try:
            self.tl_dots_frame.place_forget()
            self.br_dots_frame.place_forget()
        except Exception:
            pass

        offsets = [0.0, 0.015, 0.03, 0.032, 0.035, 0.035, 0.032, 0.03, 0.015, 0.0]

        def _step(idx: int) -> None:
            if not self.winfo_exists():
                return

            if idx < len(offsets):
                d = offsets[idx]
                if self.lbl_corner_tl:
                    self.lbl_corner_tl.place(relx=0.15 + d, rely=0.20 + d, anchor="center")
                    self.lbl_corner_tr.place(relx=0.85 - d, rely=0.20 + d, anchor="center")
                    self.lbl_corner_bl.place(relx=0.15 + d, rely=0.80 - d, anchor="center")
                    self.lbl_corner_br.place(relx=0.85 - d, rely=0.80 - d, anchor="center")

                # Change SCAN ID text color when corners move in all the way
                if d >= 0.03:
                    self.scan_id_label.configure(text_color=const.OLIN_BLUE_HOVER)
                else:
                    self.scan_id_label.configure(text_color=const.OLIN_BLUE)

                self.after(25, lambda: _step(idx + 1))
            else:
                self._is_confirming = False
                if on_complete and callable(on_complete):
                    on_complete()

        _step(0)

    def _animate_dots(self) -> None:
        """Animate square dots loading in/out in OLIN_PINK (0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 4 -> 3 -> 2 -> 1 -> 0)."""
        if not self.winfo_exists() or self._is_confirming:
            return

        try:
            for i in range(5):
                # Top-left: grows left-to-right (0 -> 1 -> 2 -> 3 -> 4)
                tl_color = const.OLIN_PINK if i < self._dots_count else const.BG_WHITE
                self.tl_dots[i].configure(fg_color=tl_color)

                # Bottom-right: grows right-to-left (4 -> 3 -> 2 -> 1 -> 0)
                br_color = const.OLIN_PINK if i >= (5 - self._dots_count) else const.BG_WHITE
                self.br_dots[i].configure(fg_color=br_color)

            if self._dots_count == 5:
                self._dots_direction = -1
            elif self._dots_count == 0:
                self._dots_direction = 1

            self._dots_count += self._dots_direction
            self.after(800, self._animate_dots)
        except Exception:
            pass
