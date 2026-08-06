"""
Select User page, with searchable dropdown selection.
"""

import math
import customtkinter as ctk
from PIL import Image

from GUI import gui_constants as const
from backend.student_roster import roster, StudentRecord


class SelectUserPage(ctk.CTkFrame):
    """
    Page allowing the user to search/select their name using a searchable text field
    with a dropdown arrow and scrollable filterable name list.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame) -> None:
        super().__init__(master)

        self.configure(fg_color=const.BG_LIGHT_BLUE)
        self._all_students: list[StudentRecord] = []
        self._filtered_students: list[StudentRecord] = []
        self._selected_student: StudentRecord | None = None
        self._dropdown_open: bool = False

        # Central container card
        card = ctk.CTkFrame(
            self,
            corner_radius=24,
            border_width=2,
            border_color=const.BORDER_BLUE,
            fg_color=const.BG_WHITE,
        )
        card.place(relx=0.5, rely=0.5, relwidth=0.88, relheight=0.82, anchor="center")
        self.card = card

        # Top-left Olin Shop Logo
        try:
            logo_path = const.STATIC_DIR / "Olin_Shop_Logo.png"
            if logo_path.exists():
                logo_img = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(
                    light_image=logo_img, dark_image=logo_img, size=(160, 60)
                )
                ctk.CTkLabel(card, image=self.logo_image, text="").place(
                    relx=0.045, rely=0.05, anchor="nw"
                )
        except (OSError, ValueError, AttributeError):
            self.logo_image = None

        # Title Label
        self.title_label = ctk.CTkLabel(
            card,
            text="Enter Your Name Below",
            font=const.FONT_HEADING,
            text_color=const.OLIN_BLUE,
            justify="center",
        )
        self.title_label.place(relx=0.5, rely=0.22, anchor="center")

        # Container for Search Bar + Arrow Button
        self.search_container = ctk.CTkFrame(
            card,
            fg_color=const.BG_WHITE,
            border_width=2,
            border_color=const.BORDER_BLUE,
            corner_radius=12,
            height=54,
            width=420,
        )
        self.search_container.place(relx=0.5, rely=0.42, anchor="center")

        # Entry for typing name with clear light grey placeholder
        self.search_entry = ctk.CTkEntry(
            self.search_container,
            placeholder_text="Enter name here",
            placeholder_text_color="#7A8B99",
            font=(const.FONT_FAMILY, 24, "bold"),
            fg_color="transparent",
            border_width=0,
            text_color=const.DARK_BLUE_TEXT,
            width=360,
            height=48,
        )
        self.search_entry.place(relx=0.02, rely=0.5, anchor="w")
        self.search_entry.bind("<KeyRelease>", self._on_type_search)
        self.search_entry.bind("<FocusIn>", lambda e: self._show_dropdown())
        self.search_entry.bind("<Return>", self._on_enter_pressed)

        self.current_arrow_frame_idx: int = 0
        self.is_arrow_hovered: bool = False
        self._arrow_anim_job = None
        self.blue_arrow_frames: list[ctk.CTkImage] = []
        self.dark_arrow_frames: list[ctk.CTkImage] = []

        # Drop-down Arrow Button precomputed frames (21 steps for smooth 180-deg ease-in-out rotation)
        try:
            blue_arrow_path = const.STATIC_DIR / "olin_arrow_blue.png"
            dark_arrow_path = const.STATIC_DIR / "olin_arrow_dark_blue.png"
            if blue_arrow_path.exists() and dark_arrow_path.exists():
                blue_img = Image.open(blue_arrow_path)
                dark_img = Image.open(dark_arrow_path)
                num_steps = 20
                for i in range(num_steps + 1):
                    p = i / float(num_steps)
                    # Cosine easing: slowest at start/end, fastest in middle
                    factor = 0.5 * (1.0 - math.cos(math.pi * p))
                    angle = 180.0 * factor

                    b_rot = blue_img.rotate(angle, resample=Image.Resampling.BICUBIC)
                    d_rot = dark_img.rotate(angle, resample=Image.Resampling.BICUBIC)

                    self.blue_arrow_frames.append(
                        ctk.CTkImage(light_image=b_rot, dark_image=b_rot, size=(22, 24))
                    )
                    self.dark_arrow_frames.append(
                        ctk.CTkImage(light_image=d_rot, dark_image=d_rot, size=(22, 24))
                    )
        except (OSError, ValueError, AttributeError) as e:
            print(f"[SelectUserPage] Arrow rotation pre-render exception: {e}")
            self.blue_arrow_frames = []
            self.dark_arrow_frames = []

        initial_img = self.blue_arrow_frames[0] if self.blue_arrow_frames else None

        self.arrow_button = ctk.CTkButton(
            self.search_container,
            text="" if initial_img else "▼",
            image=initial_img,
            font=(const.FONT_FAMILY, 16, "bold"),
            fg_color="transparent",
            hover_color=const.BG_WHITE,
            text_color=const.DARK_BLUE_TEXT,
            width=38,
            height=45,
            command=self._toggle_dropdown
        )
        self.arrow_button.place(relx=0.98, rely=0.5, anchor="e")

        self.arrow_button.bind("<Enter>", self._on_arrow_enter)
        self.arrow_button.bind("<Leave>", self._on_arrow_leave)

        # Scrollable Dropdown Frame for displaying filtered names
        self.dropdown_frame = ctk.CTkScrollableFrame(
            card,
            fg_color=const.BG_WHITE,
            border_width=2,
            border_color=const.BORDER_BLUE,
            corner_radius=12,
            width=396,
            height=120,
        )
        self.dropdown_frame.place(relx=0.5, rely=0.64, anchor="center")
        self.dropdown_frame.place_forget()  # Hidden by default

        # Next Button (disabled initially until a name is selected)
        self.next_button = ctk.CTkButton(
            card,
            text="NEXT",
            font=const.FONT_BUTTON,
            fg_color=const.CONFIRM_BLUE,
            hover_color=const.CONFIRM_BLUE_HOVER,
            text_color=const.BG_WHITE,
            corner_radius=34,
            width=170,
            height=54,
            state="disabled",
            command=self._on_next_clicked,
        )
        self.next_button.place(relx=0.5, rely=0.82, anchor="center")

        # Home Button in bottom right corner
        # (transparent background, text changes to dark blue on hover)
        self.home_button = ctk.CTkButton(
            card,
            text="HOME",
            font=const.FONT_BUTTON,
            fg_color="transparent",
            hover=False,
            text_color=const.OLIN_BLUE,
            corner_radius=0,
            width=80,
            height=36,
            command=self._on_home_clicked,
        )
        self.home_button.place(relx=0.98, rely=0.98, anchor="se")
        self.home_button.bind("<Enter>", lambda e: self.home_button.configure(text_color=const.OLIN_BLUE_HOVER))
        self.home_button.bind("<Leave>", lambda e: self.home_button.configure(text_color=const.OLIN_BLUE))

        # Load all students
        self.load_students()

    def _on_home_clicked(self) -> None:
        """Navigates back to HomePage and resets state."""
        app = self.winfo_toplevel()
        if hasattr(app, "reset_session"):
            app.reset_session()
        elif hasattr(app, "show_frame"):
            app.show_frame("HomePage")

    def load_students(self) -> None:
        """Loads all students from roster and triggers background refresh via gather_intro_data & gather_303_data."""
        self._all_students = roster.get_all_students()
        self._filtered_students = self._all_students.copy()
        self._selected_student = None
        self.search_entry.delete(0, "end")
        self.next_button.configure(state="disabled")
        self._hide_dropdown()

        app = self.winfo_toplevel()
        if hasattr(app, "run_async"):
            def _on_roster_loaded(_):
                if hasattr(self, "winfo_exists") and self.winfo_exists():
                    self._all_students = roster.get_all_students()
                    self._on_type_search()

            app.run_async(roster.refresh_from_backend(), _on_roster_loaded)


    def _toggle_dropdown(self) -> None:
        """Toggles the scrollable dropdown list open/closed."""
        if self._dropdown_open:
            self._hide_dropdown()
        else:
            self._on_type_search()
            self._show_dropdown()

    def _on_arrow_enter(self, event=None) -> None:
        self.is_arrow_hovered = True
        self._update_arrow_display()

    def _on_arrow_leave(self, event=None) -> None:
        self.is_arrow_hovered = False
        self._update_arrow_display()

    def _update_arrow_display(self) -> None:
        if not hasattr(self, "arrow_button") or not self.arrow_button.winfo_exists():
            return
        if self.blue_arrow_frames and self.dark_arrow_frames:
            frames = self.dark_arrow_frames if self.is_arrow_hovered else self.blue_arrow_frames
            idx = max(0, min(self.current_arrow_frame_idx, len(frames) - 1))
            self.arrow_button.configure(image=frames[idx])

    def _start_arrow_animation(self, target_idx: int) -> None:
        """Starts smooth ease-in-out rotation animation toward target_idx."""
        if self._arrow_anim_job is not None:
            try:
                self.after_cancel(self._arrow_anim_job)
            except (ValueError, KeyError, AttributeError, RuntimeError):
                pass
            self._arrow_anim_job = None
        self._animate_arrow_step(target_idx)

    def _animate_arrow_step(self, target_idx: int) -> None:
        if not self.winfo_exists():
            return

        if self.current_arrow_frame_idx < target_idx:
            self.current_arrow_frame_idx += 1
        elif self.current_arrow_frame_idx > target_idx:
            self.current_arrow_frame_idx -= 1

        self._update_arrow_display()

        if self.current_arrow_frame_idx != target_idx:
            self._arrow_anim_job = self.after(12, lambda: self._animate_arrow_step(target_idx))
        else:
            self._arrow_anim_job = None

    def _show_dropdown(self) -> None:
        """Shows the dropdown list and rotates arrow 180 degrees."""
        self.dropdown_frame.place(relx=0.5, rely=0.72, anchor="center")
        self.dropdown_frame.lift()
        self._dropdown_open = True
        self._start_arrow_animation(20)

    def _hide_dropdown(self) -> None:
        """Hides the dropdown list and rotates arrow back to 0 degrees."""
        self.dropdown_frame.place_forget()
        self._dropdown_open = False
        self._start_arrow_animation(0)

    def _on_type_search(self, event=None) -> None:
        """Filters names in the scrollable dropdown list based on typed query."""
        query = self.search_entry.get().strip().lower()
        if query:
            self._filtered_students = [
                s for s in self._all_students if query in s.name.lower()
            ]
        else:
            self._filtered_students = self._all_students.copy()

        # Update matching student check
        match = next((s for s in self._all_students if s.name.lower() == query), None)
        if match:
            self._selected_student = match
            self.next_button.configure(state="normal")
        else:
            self._selected_student = None
            self.next_button.configure(state="disabled")

        # Re-populate dropdown buttons
        for widget in self.dropdown_frame.winfo_children():
            widget.destroy()

        if not self._filtered_students:
            no_match_label = ctk.CTkLabel(
                self.dropdown_frame,
                text="No matching names",
                font=const.FONT_ITEM_ROW,
                text_color=const.MUTED_BLUE_TEXT,
            )
            no_match_label.pack(fill="x", pady=5)
        else:
            for student in self._filtered_students:
                btn = ctk.CTkButton(
                    self.dropdown_frame,
                    text=student.name,
                    font=const.FONT_ITEM_ROW,
                    fg_color="transparent",
                    hover_color=const.LIGHT_BLUE,
                    text_color=const.DARK_BLUE_TEXT,
                    anchor="w",
                    height=34,
                    command=lambda s=student: self._select_student(s),
                )
                btn.pack(fill="x", pady=1)

        self._show_dropdown()

    def _select_student(self, student: StudentRecord) -> None:
        """Sets selected student from list click."""
        self._selected_student = student
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, student.name)
        self.next_button.configure(state="normal")
        self._hide_dropdown()

    def _on_enter_pressed(self, event=None) -> str | None:
        """Handles Enter key press in the search bar. Submits if valid."""
        if self._selected_student:
            self._on_next_clicked()
            return "break"
        return None

    def _on_next_clicked(self) -> None:
        """Handles Next button click to start session and navigate to BorrowedItemsPage."""
        if not self._selected_student:
            return

        app = self.winfo_toplevel()
        if hasattr(app, "session"):
            app.session.select_student(self._selected_student)

        # Trigger user session load and navigate to BorrowedItemsPage
        if hasattr(app, "_handle_id_scan"):
            app._handle_id_scan(self._selected_student.email)
        elif hasattr(app, "_handle_user_id_scanned"):
            app._handle_user_id_scanned(self._selected_student.email)
        elif hasattr(app, "show_frame"):
            app.show_frame("BorrowedItemsPage")

    def update_scale(self, scale: float) -> None:
        """
        Dynamically scale fonts, search entry,
        dropdown, and next button when screen size changes.
        """
        new_title_size = max(24, int(52 * scale))
        new_btn_size = max(14, int(26 * scale))

        self.title_label.configure(font=(const.FONT_FAMILY, new_title_size, "bold"))
        self.search_container.configure(
            width=max(200, int(420 * scale)), height=max(36, int(54 * scale))
        )
        self.search_entry.configure(
            font=(const.FONT_FAMILY, new_btn_size, "bold"),
            width=max(160, int(360 * scale)),
            height=max(30, int(48 * scale)),
        )
        self.dropdown_frame.configure(
            width=max(180, int(396 * scale)), height=max(80, int(140 * scale))
        )
        self.next_button.configure(
            font=(const.FONT_FAMILY, new_btn_size, "bold"),
            width=max(120, int(220 * scale)),
            height=max(36, int(54 * scale)),
        )
        self.home_button.configure(
            font=(const.FONT_FAMILY, max(12, int(20 * scale)), "bold"),
            width=max(60, int(110 * scale)),
            height=max(28, int(44 * scale)),
        )

        if hasattr(self, "logo_image") and self.logo_image:
            w = max(60, int(160 * scale))
            h = max(22, int(60 * scale))
            self.logo_image.configure(size=(w, h))

        if hasattr(self, "blue_arrow_frames"):
            w = max(10, int(22 * scale))
            h = max(12, int(24 * scale))
            for img in self.blue_arrow_frames:
                img.configure(size=(w, h))

        if hasattr(self, "dark_arrow_frames"):
            w = max(10, int(22 * scale))
            h = max(12, int(24 * scale))
            for img in self.dark_arrow_frames:
                img.configure(size=(w, h))
