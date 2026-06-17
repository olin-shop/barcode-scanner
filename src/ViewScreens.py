import customtkinter as ctk
from PIL import Image

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
            ScanIDPage,
            BorrowedItemsPage,
            ConfirmBorrowPage,
            ConfirmReturnPage,
            FinalConfirmationPage,
            SessionTimeoutPage,
        ):
            frame = F(self)
            self.frames[F.__name__] = frame

            frame.place(
                relx=0,
                rely=0,
                relwidth=1,
                relheight=1
            )

        self.show_frame("ScanIDPage")

    def show_frame(self, page_name):
        self.frames[page_name].tkraise()


# =====================================================
# PAGE 1: SCAN ID
# =====================================================

class ScanIDPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        dark_green = "#2E7D32"
        light_green = "#81C784"

        self.configure(fg_color=dark_green)

        img = Image.open("green_corner.png")
        self.corner_tl = ctk.CTkImage(
            light_image=img,
            dark_image=img,
            size=(90, 90)
        )
        self.corner_tl = ctk.CTkImage(
            light_image=img,
            dark_image=img,
            size=(90, 90)   # Adjust size as needed
        )
        self.corner_tr = ctk.CTkImage(
            light_image=img.rotate(270, expand=True),
            dark_image=img.rotate(270, expand=True),
            size=(90, 90)
        )
        self.corner_bl = ctk.CTkImage(
            light_image=img.rotate(90, expand=True),
            dark_image=img.rotate(90, expand=True),
            size=(90, 90)
        )
        self.corner_br = ctk.CTkImage(
            light_image=img.rotate(180, expand=True),
            dark_image=img.rotate(180, expand=True),
            size=(80, 80)
        )

        ctk.CTkLabel(self, image=self.corner_tl, text="").place(relx=.2, rely=.2,anchor="center")
        ctk.CTkLabel(self, image=self.corner_tr, text="").place(relx=.8, rely=.2,anchor="center")
        ctk.CTkLabel(self, image=self.corner_bl, text="").place(relx=.2, rely=.8,anchor="center")
        ctk.CTkLabel(self, image=self.corner_br, text="").place(relx=.8, rely=.8,anchor="center")
        
        # Main text
        label = ctk.CTkLabel(
            self,
            text="SCAN ID",
            font=("Arial", 88, "bold"),
            text_color="white"
        )

        label.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )



# =====================================================
# PAGE 2: BORROWED ITEMS
# =====================================================
# =====================================================
# PAGE 2: BORROWED ITEMS
# =====================================================

class BorrowedItemsPage(ctk.CTkFrame):

    def __init__(self, master, borrowed_items=None):
        """
        borrowed_items: list of (item_name: str, borrowed_at: datetime) tuples.
                        Pass None or an empty list to start with no items shown.
        """
        super().__init__(master)

        title = ctk.CTkLabel(
            self,
            text="Current Borrowed Items",
            font=("Arial", 32, "bold")
        )
        title.pack(pady=20)

        # Scrollable frame for items
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            width=400,
            height=300
        )
        self.scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        instruction = ctk.CTkLabel(
            self,
            text="Scan an item to borrow or return",
            font=("Arial", 18)
        )
        instruction.pack(side="bottom", pady=20)

        # Populate with initial data
        self.refresh(borrowed_items or [])

    def refresh(self, borrowed_items):
        """
        Clears and repopulates the list.

        borrowed_items: list of (item_name: str, borrowed_at: datetime) tuples.

        Example:
            from datetime import datetime
            items = [
                ("Multimeter",  datetime(2025, 6, 14, 9, 30)),
                ("Oscilloscope", datetime(2025, 6, 15, 14, 5)),
            ]
            app.frames["BorrowedItemsPage"].refresh(items)
        """
        # Clear existing rows
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        for item_name, borrowed_at in borrowed_items:
            date_str = borrowed_at.strftime("%b %d, %Y  %H:%M")

            row = ctk.CTkFrame(
                self.scroll_frame,
                fg_color="transparent"
            )
            row.pack(fill="x", pady=4, padx=10)

            # Item name button (left-aligned, triggers popup)
            btn = ctk.CTkButton(
                row,
                text=f"• {item_name}",
                font=("Arial", 24),
                anchor="w",
                fg_color="transparent",
                text_color=("black", "white"),
                hover_color=("gray85", "gray25"),
                command=lambda i=item_name: self.show_missing_popup(i)
            )
            btn.pack(side="left", fill="x", expand=True)

            # Borrow date (right-aligned)
            date_label = ctk.CTkLabel(
                row,
                text=date_str,
                font=("Arial", 16),
                text_color=("gray40", "gray70"),
                anchor="e"
            )
            date_label.pack(side="right", padx=(10, 0))

    def show_missing_popup(self, item_name):
        popup = ctk.CTkToplevel(self)
        popup.title("Mark as Missing")
        popup.overrideredirect(True)
        popup.update_idletasks()
        x = app.winfo_x() + (app.winfo_width() // 2) - 150
        y = app.winfo_y() + (app.winfo_height() // 2) - 100
        popup.geometry(f"300x130+{x}+{y}")
        popup.grab_set()

        label = ctk.CTkLabel(
            popup,
            text=f"Mark '{item_name}' as missing?",
            font=("Arial", 16),
            wraplength=260
        )
        label.pack(pady=30)

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack()

        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="Mark Missing",
            fg_color="red",
            hover_color="darkred",
            command=lambda: self.mark_missing(item_name, popup)
        )
        confirm_btn.pack(side="left", padx=10)

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=popup.destroy
        )
        cancel_btn.pack(side="right", padx=10)

    def mark_missing(self, item_name, popup):
        print(f"{item_name} marked as missing")  # Replace with real logic
        popup.destroy()
'''
class BorrowedItemsPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        title = ctk.CTkLabel(
            self,
            text="Current Borrowed Items",
            font=("Arial", 32, "bold")
        )
        title.pack(pady=20)

        # Scrollable frame for items
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            width=400,
            height=300
        )
        self.scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        items = ["Item 1", "Item 2", "Item 3"]
        for item in items:
            btn = ctk.CTkButton(
                self.scroll_frame,
                text=f"• {item}",
                font=("Arial", 24),
                anchor="w",
                fg_color="transparent",
                text_color=("black", "white"),
                hover_color=("gray85", "gray25"),
                command=lambda i=item: self.show_missing_popup(i)
            )
            btn.pack(fill="x", pady=4, padx=10)

        instruction = ctk.CTkLabel(
            self,
            text="Scan an item to borrow or return",
            font=("Arial", 18)
        )
        instruction.pack(side="bottom", pady=20)

    def show_missing_popup(self, item_name):
        popup = ctk.CTkToplevel(self)
        popup.title("Mark as Missing")
        popup.overrideredirect(True)  # Remove title bar
        # Center on screen
        popup.update_idletasks()  # Ensure geometry is calculated
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        x = app.winfo_x() + (app.winfo_width() // 2) - 150
        y = app.winfo_y() + (app.winfo_height() // 2) - 100
        # Apply the geometry
        popup.geometry(f"300x200+{x}+{y}")
        popup.grab_set()  # Make popup modal

        label = ctk.CTkLabel(
            popup,
            text=f"Mark '{item_name}' as missing?",
            font=("Arial", 16),
            wraplength=260
        )
        label.pack(pady=30)

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack()

        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="Mark Missing",
            fg_color="red",
            hover_color="darkred",
            command=lambda: self.mark_missing(item_name, popup)
        )
        confirm_btn.pack(side="left", padx=10)

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=popup.destroy
        )
        cancel_btn.pack(side="left", padx=10)

    def mark_missing(self, item_name, popup):
        print(f"{item_name} marked as missing")  # Replace with real logic
        popup.destroy()
'''

# =====================================================
# PAGE 3: CONFIRM BORROW
# =====================================================

class ConfirmBorrowPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        title = ctk.CTkLabel(
            self,
            text="Borrow Item?",
            font=("Arial", 36, "bold")
        )
        title.pack(pady=30)

        item = ctk.CTkLabel(
            self,
            text="Item Name",
            font=("Arial", 28)
        )
        item.pack(pady=20)

        button_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        button_frame.pack(pady=40)

        ctk.CTkButton(
            button_frame,
            fg_color="#19ca63",      
            hover_color="#219250",   
            text="Confirm",
            font=("Arial", 30),
            width=180,
            height=60
        ).pack(side="left", padx=20)

        ctk.CTkButton(
            button_frame,
            fg_color="#cd2828",      
            hover_color="#922121", 
            text="Cancel",
            font=("Arial", 30),
            width=180,
            height=60
        ).pack(side="left", padx=20)


# =====================================================
# PAGE 4: CONFIRM RETURN
# =====================================================

class ConfirmReturnPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        title = ctk.CTkLabel(
            self,
            text="Return Item?",
            font=("Arial", 36, "bold")
        )
        title.pack(pady=30)

        item = ctk.CTkLabel(
            self,
            text="Item Name",
            font=("Arial", 28)
        )
        item.pack(pady=20)

        button_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        button_frame.pack(pady=40)

        ctk.CTkButton(
            button_frame,
            text="Confirm",
            width=180,
            height=60
        ).pack(side="left", padx=20)

        ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=180,
            height=60
        ).pack(side="left", padx=20)


# =====================================================
# PAGE 5: FINAL CONFIRMATION
# =====================================================

class FinalConfirmationPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        label = ctk.CTkLabel(
            self,
            text="Confirmed",
            font=("Arial", 80, "bold")
        )
        label.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )
        sublabel = ctk.CTkLabel(
            self,
            text="Closing session..",
            font=("Arial", 30, "italic")
        )
        sublabel.place(
            relx=0.5,
            rely=0.7,
            anchor="center"
        )

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



from datetime import datetime
import threading

app = App()

test_items = [
    ("Multimeter",    datetime(2025, 6, 14,  9, 30)),
    ("Oscilloscope",  datetime(2025, 6, 15, 14,  5)),
    ("Power Supply",  datetime(2025, 6, 16, 11,  0)),
    ("Soldering Iron",datetime(2025, 6, 16, 13, 45)),
]
app.frames["BorrowedItemsPage"].refresh(test_items)

VALID_PAGES = [
    "ScanIDPage",
    "BorrowedItemsPage",
    "ConfirmBorrowPage",
    "ConfirmReturnPage",
    "FinalConfirmationPage",
    "SessionTimeoutPage",
]

def terminal_input_loop():
    while True:
        try:
            user_input = input("Enter page name: ").strip()
        except EOFError:
            break

        if not user_input:
            continue

        # Case-insensitive match
        match = next((p for p in VALID_PAGES if p.lower() == user_input.lower()), None)

        if match:
            app.after(0, lambda m=match: app.show_frame(m))
            print(f"  → Switched to {match}")
        else:
            print(f"  ✗ Unknown page '{user_input}'. Valid pages:")
            for p in VALID_PAGES:
                print(f"      {p}")

input_thread = threading.Thread(target=terminal_input_loop, daemon=True)
input_thread.start()

app.mainloop()