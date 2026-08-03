"""
Select User page, with searchable dropdown selection.
"""

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
        except Exception:
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

        # Entry for typing name with light grey placeholder
        self.search_entry = ctk.CTkEntry(
            self.search_container,
            placeholder_text="Enter name here",
            placeholder_text_color="#A0A0A0",
            font=const.FONT_BUTTON,
            fg_color="transparent",
            border_width=0,
            text_color=const.DARK_BLUE_TEXT,
            width=360,
            height=48,
        )
        self.search_entry.place(relx=0.02, rely=0.5, anchor="w")
        self.search_entry.bind("<KeyRelease>", self._on_type_search)
        self.search_entry.bind("<FocusIn>", lambda e: self._show_dropdown())

        # Drop-down Arrow Button on the right
        self.arrow_button = ctk.CTkButton(
            self.search_container,
            text="▼",
            font=(const.FONT_FAMILY, 14, "bold"),
            fg_color="transparent",
            hover_color=const.LIGHT_BLUE,
            text_color=const.DARK_BLUE_TEXT,
            width=38,
            height=48,
            command=self._toggle_dropdown,
        )
        self.arrow_button.place(relx=0.98, rely=0.5, anchor="e")

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
            text="Next",
            font=const.FONT_BUTTON,
            fg_color=const.CONFIRM_BLUE,
            hover_color=const.CONFIRM_BLUE_HOVER,
            text_color=const.BG_WHITE,
            corner_radius=12,
            width=220,
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
        self.home_button.bind(
            "<Enter>",
            lambda e: self.home_button.configure(text_color=const.DARK_BLUE_TEXT),
        )
        self.home_button.bind(
            "<Leave>", lambda e: self.home_button.configure(text_color=const.OLIN_BLUE)
        )

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
        """Loads all students from roster."""
        self._all_students = roster.get_all_students()
        self._filtered_students = self._all_students.copy()
        self._selected_student = None
        self.search_entry.delete(0, "end")
        self.next_button.configure(state="disabled")
        self._hide_dropdown()

    def _toggle_dropdown(self) -> None:
        """Toggles the scrollable dropdown list open/closed."""
        if self._dropdown_open:
            self._hide_dropdown()
        else:
            self._on_type_search()
            self._show_dropdown()

    def _show_dropdown(self) -> None:
        """Shows the dropdown list."""
        self.dropdown_frame.place(relx=0.5, rely=0.72, anchor="center")
        self.dropdown_frame.lift()
        self._dropdown_open = True

    def _hide_dropdown(self) -> None:
        """Hides the dropdown list."""
        self.dropdown_frame.place_forget()
        self._dropdown_open = False

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
