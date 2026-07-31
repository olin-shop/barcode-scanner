import math
import customtkinter as ctk
from PIL import Image

from GUI import gui_constants as const

# =====================================================
# LOADING PAGE
# =====================================================

class LoadingPage(ctk.CTkFrame):
    """
    Loading page displayed during asynchronous background requests.
    Features animated "Loading..." text with dual high-FPS slanted rhombus progress bars.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame) -> None:
        super().__init__(master)

        self.configure(fg_color=const.BG_LIGHT_BLUE)

        # Central white card container
        card = ctk.CTkFrame(
            self,
            corner_radius=24,
            border_width=2,
            border_color=const.BORDER_BLUE,
            fg_color=const.BG_WHITE
        )
        card.place(relx=0.5, rely=0.5, relwidth=0.88, relheight=0.82, anchor="center")

        # Top-left Olin Shop Logo
        try:
            logo_path = const.STATIC_DIR / "Olin_Shop_Logo.png"
            if logo_path.exists():
                logo_img = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(160, 60))
                ctk.CTkLabel(card, image=self.logo_image, text="").place(relx=0.045, rely=0.05, anchor="nw")
        except Exception:
            pass

        # Central vertical container holding Loading text and animated progress canvas
        center_frame = ctk.CTkFrame(card, fg_color="transparent")
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        # "Loading..." text container frame
        self.text_container = ctk.CTkFrame(center_frame, fg_color="transparent")
        self.text_container.pack(side="top", pady=(0, 20))

        self.loading_label = ctk.CTkLabel(
            self.text_container,
            text="Loading",
            font=const.FONT_LOADING,
            text_color=const.OLIN_BLUE
        )
        self.loading_label.pack(side="left")

        self.dots_label = ctk.CTkLabel(
            self.text_container,
            text="...",
            font=const.FONT_LOADING,
            text_color=const.OLIN_BLUE,
            width=60,
            anchor="w"
        )
        self.dots_label.pack(side="left")

        # Canvas for the dual 70-degree slanted rhombus progress animation
        self.canvas_width = 800
        self.canvas_height = 30
        self.anim_canvas = ctk.CTkCanvas(
            card,
            height=self.canvas_height,
            bg=const.BG_WHITE,
            highlightthickness=0,
            bd=0
        )
        self.anim_canvas.place(relx=0.5, rely=0.65, relwidth=0.995, anchor="center")

        def _on_canvas_configure(event=None) -> None:
            if event and event.width > 1:
                self.canvas_width = event.width

        self.anim_canvas.bind("<Configure>", _on_canvas_configure)

        self._dots = 3
        self._dots_timer_counter = 0

        # Primary Pink Rhombus (Shape 1: 400px length, 30px height)
        self._shape_width = 400
        self._shape_x = -self._shape_width

        # Secondary Blue Rhombus (Shape 2: 600px length, 7.5px height, layered on top)
        self._shape2_length = 600
        self._shape2_height = 7.5
        self._shape2_x = -self._shape2_length - 100

        self._animate()

    def _animate(self) -> None:
        """Continuously translates both slanted polygon shapes left-to-right at high FPS (~125 FPS)."""
        try:
            if not self.winfo_exists():
                return

            # Clear previous canvas frame
            self.anim_canvas.delete("all")

            # 70-degree slant calculation (matches top banner geometry in BorrowedItemsPage)
            shape_h = self.canvas_height
            dx = shape_h / math.tan(math.radians(70))

            # 1. Primary Pink Rhombus (Background shape)
            top_left_x1 = self._shape_x
            top_right_x1 = self._shape_x + self._shape_width
            bot_right_x1 = top_right_x1 - dx
            bot_left_x1 = top_left_x1 - dx

            points1 = [
                top_left_x1, 0,
                top_right_x1, 0,
                bot_right_x1, shape_h,
                bot_left_x1, shape_h
            ]

            self.anim_canvas.create_polygon(
                points1,
                fill=const.OLIN_PINK,
                outline=""
            )

            # 2. Secondary Blue Rhombus (1.5x length = 600px, 1/4 width = 7.5px height, OLIN_BLUE_HOVER)
            h2 = self._shape2_height
            y_top = (shape_h - h2) / 2.0
            y_bot = y_top + h2
            dx2 = h2 / math.tan(math.radians(70))

            top_left_x2 = self._shape2_x
            top_right_x2 = self._shape2_x + self._shape2_length
            bot_right_x2 = top_right_x2 - dx2
            bot_left_x2 = top_left_x2 - dx2

            points2 = [
                top_left_x2, y_top,
                top_right_x2, y_top,
                bot_right_x2, y_bot,
                bot_left_x2, y_bot
            ]

            # Rendered over the pink rhombus
            self.anim_canvas.create_polygon(
                points2,
                fill=const.OLIN_BLUE_HOVER,
                outline=""
            )

            # Advance shape positions rightward at high FPS (8ms timer interval)
            self._shape_x += 2.5
            if self._shape_x > self.canvas_width + dx + 10:
                self._shape_x = -self._shape_width - 10

            self._shape2_x += 4.5
            if self._shape2_x > self.canvas_width + dx2 + 10:
                self._shape2_x = -self._shape2_length - 10

            # Update dots text every ~600ms (75 frames * 8ms = 600ms)
            self._dots_timer_counter += 1
            if self._dots_timer_counter >= 75:
                self._dots_timer_counter = 0
                dots_str = "." * self._dots
                self.dots_label.configure(text=dots_str)
                self._dots = (self._dots % 3) + 1

            self.after(8, self._animate)
        except Exception:
            pass
