import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk, ImageEnhance, ImageOps
import fitz  # PyMuPDF
import os
import sys
import random
import json
import pyperclip
import time

class ToolTip:
    """Create a tooltip for a given widget"""
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<ButtonPress>', self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"), padx=4, pady=2)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class PDFViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("BareReader")
        self.tabs = {}
        self.last_tab = None
        self.used_colors = set()

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.geometry(f"{int(screen_width * 0.8)}x{int(screen_height * 0.8)}+{int(screen_width * 0.1)}+{int(screen_height * 0.1)}")
        
        # Configure modern color scheme
        self.colors = {
            'bg': '#f5f5f5',
            'fg': '#2c3e50',
            'accent': '#3498db',
            'accent_hover': '#2980b9',
            'success': '#27ae60',
            'danger': '#e74c3c',
            'warning': '#f39c12',
            'border': '#bdc3c7',
            'toolbar_bg': '#ecf0f1',
            'dark_bg': '#1e1e1e',
            'dark_fg': '#e0e0e0',
            'dark_toolbar': '#2d2d2d',
            'dark_border': '#404040'
        }
        
        root.configure(bg=self.colors['bg'])

        # Modern toolbar with organized button groups (at the very top)
        toolbar_frame = tk.Frame(root, bg=self.colors['toolbar_bg'], relief='flat', bd=0)
        toolbar_frame.pack(side="top", fill="x", padx=0, pady=0)
        
        # Create button style
        self.setup_button_styles()
        
        # File operations group
        file_group = tk.Frame(toolbar_frame, bg=self.colors['toolbar_bg'])
        file_group.pack(side="left", padx=8, pady=8)
        
        self.btn_open = self.create_modern_button(file_group, "📂 Abrir", self.open_pdf, 
                                                  tooltip="Abrir archivo PDF o ePub")
        
        self.btn_close = self.create_modern_button(file_group, "✕ Cerrar", self.confirm_close_current_tab,
                                                   tooltip="Cerrar pestaña actual", color='danger')
        
        # Separator
        sep1 = tk.Frame(toolbar_frame, bg=self.colors['border'], width=1)
        sep1.pack(side="left", fill="y", padx=5, pady=8)
        
        # Navigation group
        nav_group = tk.Frame(toolbar_frame, bg=self.colors['toolbar_bg'])
        nav_group.pack(side="left", padx=8, pady=8)
        
        self.btn_prev = self.create_modern_button(nav_group, "◀ Anterior", self.prev_page,
                                                   tooltip="Página anterior")
        
        self.btn_next = self.create_modern_button(nav_group, "Siguiente ▶", self.next_page,
                                                   tooltip="Página siguiente")
        
        # Page navigation
        page_frame = tk.Frame(nav_group, bg=self.colors['toolbar_bg'])
        page_frame.pack(side="left", padx=(10, 0))
        
        tk.Label(page_frame, text="Página:", bg=self.colors['toolbar_bg'], 
                fg=self.colors['fg'], font=('Segoe UI', 9)).pack(side="left", padx=(0, 5))
        
        self.page_entry = tk.Entry(page_frame, width=6, font=('Segoe UI', 9),
                                   relief='solid', borderwidth=1, highlightthickness=1,
                                   highlightbackground=self.colors['border'],
                                   highlightcolor=self.colors['accent'])
        self.page_entry.pack(side="left", padx=2)
        self.page_entry.bind('<Return>', lambda e: self.go_to_page())
        
        self.btn_go = self.create_modern_button(page_frame, "Ir", self.go_to_page,
                                                tooltip="Ir a página específica")
        
        # Separator
        sep2 = tk.Frame(toolbar_frame, bg=self.colors['border'], width=1)
        sep2.pack(side="left", fill="y", padx=5, pady=8)
        
        # Zoom group
        zoom_group = tk.Frame(toolbar_frame, bg=self.colors['toolbar_bg'])
        zoom_group.pack(side="left", padx=8, pady=8)
        
        self.btn_zoom_out = self.create_modern_button(zoom_group, "🔍−", self.zoom_out,
                                                      tooltip="Alejar (Zoom -)")
        
        self.btn_zoom_in = self.create_modern_button(zoom_group, "🔍+", self.zoom_in,
                                                     tooltip="Acercar (Zoom +)")
        
        # Separator
        sep3 = tk.Frame(toolbar_frame, bg=self.colors['border'], width=1)
        sep3.pack(side="left", fill="y", padx=5, pady=8)
        
        # Theme toggle
        theme_group = tk.Frame(toolbar_frame, bg=self.colors['toolbar_bg'])
        theme_group.pack(side="left", padx=8, pady=8)
        
        self.btn_dark = self.create_modern_button(theme_group, "🌙 Oscuro", self.toggle_dark_mode,
                                                  tooltip="Alternar modo oscuro/claro")

        # Modern tab frame with better styling (below toolbar)
        self.tab_frame = tk.Frame(root, bg=self.colors['bg'], height=40)
        self.tab_frame.pack(side="top", fill="x", padx=0, pady=0)
        self.tab_control = ttk.Notebook(self.tab_frame)
        
        # Style the notebook
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background=self.colors['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', padding=[12, 6], font=('Segoe UI', 9))
        style.map('TNotebook.Tab',
                 background=[('selected', self.colors['accent']), ('!selected', self.colors['toolbar_bg'])],
                 foreground=[('selected', 'white'), ('!selected', self.colors['fg'])],
                 expand=[('selected', [1, 1, 1, 0])])
        
        self.tab_control.pack(fill="x", padx=5, pady=5)
        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.active_tab_data = None

        self.canvas_frame = tk.Frame(root, bg=self.colors['bg'])
        self.canvas_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.canvas = tk.Canvas(self.canvas_frame, bg="#ffffff", highlightthickness=0, relief='flat')
        
        # Modern scrollbars
        scrollbar_style = ttk.Style()
        scrollbar_style.theme_use('clam')
        scrollbar_style.configure("Modern.Vertical.TScrollbar",
                                 background=self.colors['toolbar_bg'],
                                 troughcolor=self.colors['bg'],
                                 borderwidth=0,
                                 arrowcolor=self.colors['fg'],
                                 darkcolor=self.colors['border'],
                                 lightcolor=self.colors['border'])
        scrollbar_style.configure("Modern.Horizontal.TScrollbar",
                                 background=self.colors['toolbar_bg'],
                                 troughcolor=self.colors['bg'],
                                 borderwidth=0,
                                 arrowcolor=self.colors['fg'],
                                 darkcolor=self.colors['border'],
                                 lightcolor=self.colors['border'])
        
        self.v_scroll = ttk.Scrollbar(self.canvas_frame, orient="vertical", 
                                      command=self.canvas.yview, style="Modern.Vertical.TScrollbar")
        self.h_scroll = ttk.Scrollbar(self.canvas_frame, orient="horizontal", 
                                      command=self.canvas.xview, style="Modern.Horizontal.TScrollbar")
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.v_scroll.pack(side="right", fill="y", padx=(0, 0))
        self.h_scroll.pack(side="bottom", fill="x", pady=(0, 0))
        self.canvas.pack(side="left", fill="both", expand=True)

        self.root.bind("<KeyPress-Up>", self.scroll_up)
        self.root.bind("<KeyPress-Down>", self.scroll_down)
        self.root.bind("<Configure>", self.on_resize)
        self.image_container = self.canvas.create_image(0, 0, anchor='n')

        self.zoom = 1.0  # Default zoom (no scaling)

        self.root.bind("<MouseWheel>", self.on_mouse_scroll)
        self.root.bind("<Button-4>", self.on_mouse_scroll)
        self.root.bind("<Button-5>", self.on_mouse_scroll)
        # Bind mouse wheel to canvas for better scrolling
        self.canvas.bind("<MouseWheel>", self.on_canvas_scroll)
        self.canvas.bind("<Button-4>", self.on_canvas_scroll)
        self.canvas.bind("<Button-5>", self.on_canvas_scroll)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Track mouse events for selection
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)

        # Selection data
        self.selection_start = None
        self.selection_end = None

        self.current_page = 0
        self.page_count = 0
        self.pdf_path = None
        self.current_image = None
        self.zoom = 1.5
        self.dark_mode = True  # Dark mode by default
        self.current_doc = None
        
        # Apply dark mode by default
        self.root.after(100, self.apply_dark_mode)

        session_path = self.get_session_path()
        if os.path.exists(session_path):
            try:
                with open(session_path, "r") as f:
                    session = json.load(f)
                    # Check if it's the new format with tabs
                    if "tabs" in session:
                        tabs_data = session.get("tabs", [])
                        active_index = session.get("active_index", 0)
                        # Use saved dark mode or default to True
                        self.dark_mode = session.get("dark_mode", True)
                        # Apply the theme
                        self.root.after(100, self.apply_dark_mode)
                        
                        # Restore all tabs
                        for idx, tab_info in enumerate(tabs_data):
                            file_path = tab_info.get("pdf_path")
                            if file_path and os.path.exists(file_path):
                                self.restore_tab_from_session(tab_info, idx == active_index)
                    else:
                        # Old format - single file
                        self.pdf_path = session.get("pdf_path")
                        self.current_page = session.get("page", 0)
                        self.zoom = session.get("zoom", 1.5)
                        if self.pdf_path and os.path.exists(self.pdf_path):
                            self.restore_last_session()
            except Exception as e:
                print(f"Error loading last session: {e}")

    def get_session_path(self):
        import os
        return os.path.join(os.getenv("APPDATA"), "BareReader", "last_session.json")

    def restore_last_session(self):
        """Legacy method for old session format"""
        file_name = os.path.basename(self.pdf_path)
        tab_info = {
            "file_name": file_name,
            "pdf_path": self.pdf_path,
            "current_page": self.current_page,
            "zoom": self.zoom,
            "scroll": 0.0,
            "color": None
        }
        self.restore_tab_from_session(tab_info, True)
    
    def restore_tab_from_session(self, tab_info, is_active=False):
        """Restore a single tab from session data"""
        file_path = tab_info.get("pdf_path")
        file_name = tab_info.get("file_name", os.path.basename(file_path))
        current_page = tab_info.get("current_page", 0)
        zoom = tab_info.get("zoom", 1.5)
        scroll = tab_info.get("scroll", 0.0)
        saved_color = tab_info.get("color")
        
        # Check if tab already exists
        if file_name in self.tabs:
            if is_active:
                self.tab_control.select(self.tabs[file_name]['frame'])
            return
        
        new_tab = tk.Frame(self.tab_control)
        
        # Use saved color or generate new one
        if saved_color:
            tab_color = saved_color
        else:
            while True:
                color = f'#{random.randint(50,200):02x}{random.randint(50,200):02x}{random.randint(50,200):02x}'
                if color not in self.used_colors:
                    self.used_colors.add(color)
                    tab_color = color
                    break
        
        emoji = "🔄"
        tab_text = f"{emoji} {file_name}"
        self.tab_control.add(new_tab, text=tab_text)
        
        if is_active:
            self.tab_control.select(new_tab)

        color_bar = tk.Frame(new_tab, width=10, bg=tab_color)
        color_bar.pack(side="left", fill="y")

        try:
            # PyMuPDF can open both PDF and ePub files
            doc = fitz.open(file_path)
        except Exception as e:
            file_type = "PDF/ePub" if file_path.lower().endswith('.epub') else "PDF"
            messagebox.showerror("Error", f"Failed to open {file_type}.\n\n{e}")
            return

        self.tabs[file_name] = {
            "frame": new_tab,
            "pdf_path": file_path,
            "current_page": current_page,
            "zoom": zoom,
            "color": tab_color,
            "scroll": scroll,
            "doc": doc
        }

        if is_active:
            self.active_tab_data = self.tabs[file_name]
            self.pdf_path = file_path
            self.current_doc = doc
            self.page_count = len(doc)
            self.current_page = current_page
            self.zoom = zoom
            self.last_tab = new_tab
            self.load_page_image()
            # Restore scroll position if available
            self.show_page(restore_scroll=scroll if scroll > 0 else None)

    def on_close(self):
        try:
            # Save all tabs to session
            session_path = self.get_session_path()
            os.makedirs(os.path.dirname(session_path), exist_ok=True)
            
            # Save current tab state before closing
            if self.active_tab_data and self.pdf_path:
                for name, tab_data in self.tabs.items():
                    if tab_data == self.active_tab_data:
                        tab_data['current_page'] = self.current_page
                        tab_data['zoom'] = self.zoom
                        tab_data['scroll'] = self.canvas.yview()[0] if self.canvas.yview() else 0.0
                        break
            
            # Build session data with all tabs
            tabs_data = []
            for name, tab_data in self.tabs.items():
                tabs_data.append({
                    "file_name": name,
                    "pdf_path": tab_data['pdf_path'],
                    "current_page": tab_data['current_page'],
                    "zoom": tab_data['zoom'],
                    "scroll": tab_data.get('scroll', 0.0),
                    "color": tab_data['color']
                })
            
            # Save active tab index
            active_index = 0
            if self.tabs and self.active_tab_data:
                tab_list = list(self.tabs.items())
                for idx, (name, tab_data) in enumerate(tab_list):
                    if tab_data == self.active_tab_data:
                        active_index = idx
                        break
            
            with open(session_path, "w") as f:
                json.dump({
                    "tabs": tabs_data,
                    "active_index": active_index,
                    "dark_mode": self.dark_mode
                }, f)
        except Exception as e:
            print(f"Error saving session: {e}")
        finally:
            # Close all documents
            for name, tab_data in self.tabs.items():
                try:
                    tab_data['doc'].close()
                except:
                    pass
            self.root.destroy()
        
    def on_resize(self, event):
        if self.pdf_path:
            self.fit_to_width()

    def open_pdf(self):
        filepath = filedialog.askopenfilename(
            filetypes=[
                ("PDF Files", "*.pdf"),
                ("ePub Files", "*.epub"),
                ("All Supported", "*.pdf;*.epub")
            ]
        )
        if filepath:
            file_name = os.path.basename(filepath)
            if file_name in self.tabs:
                self.tab_control.select(self.tabs[file_name]['frame'])
                # Update active tab data
                self.active_tab_data = self.tabs[file_name]
                self.pdf_path = self.tabs[file_name]['pdf_path']
                self.current_doc = self.tabs[file_name]['doc']
                self.current_page = self.tabs[file_name]['current_page']
                self.zoom = self.tabs[file_name]['zoom']
                self.page_count = len(self.current_doc)
                self.load_page_image()
                scroll_value = self.tabs[file_name].get('scroll', 0.0)
                # Restore scroll position if available
                self.show_page(restore_scroll=scroll_value if scroll_value > 0 else None)
                return

            new_tab = tk.Frame(self.tab_control)
            while True:
                color = f'#{random.randint(50,200):02x}{random.randint(50,200):02x}{random.randint(50,200):02x}'
                if color not in self.used_colors:
                    self.used_colors.add(color)
                    break

            tab_color = color
            colors = ["🟥", "🟦", "🟩", "🟨", "🟪", "🟫"]
            emoji = colors[len(self.used_colors) % len(colors)]
            tab_text = f"{emoji} {file_name}"
            self.tab_control.add(new_tab, text=tab_text)
            self.tab_control.select(new_tab)

            color_bar = tk.Frame(new_tab, width=10, bg=tab_color)
            color_bar.pack(side="left", fill="y")

            try:
                # PyMuPDF can open both PDF and ePub files
                doc = fitz.open(filepath)
                # If it's an ePub, convert it to PDF-like format for rendering
                if filepath.lower().endswith('.epub'):
                    # ePub files are handled similarly to PDFs by PyMuPDF
                    pass
            except Exception as e:
                file_type = "PDF/ePub" if filepath.lower().endswith('.epub') else "PDF"
                messagebox.showerror("Error", f"Failed to open {file_type}.\n\n{e}")
                return

            self.tabs[file_name] = {
                "frame": new_tab,
                "pdf_path": filepath,
                "current_page": 0,
                "zoom": 1.5,
                "color": tab_color,
                "scroll": 0.0,
                "doc": doc
            }

            # Set as active tab
            self.active_tab_data = self.tabs[file_name]
            self.pdf_path = filepath
            self.current_doc = doc
            self.page_count = len(doc)
            self.current_page = 0
            self.zoom = 1.5
            self.last_tab = new_tab
            self.load_page_image()
            # Always start from top for new documents
            self.show_page(restore_scroll=None)

    def on_tab_change(self, event=None):
        if event is None:
            # Called programmatically - get current selection
            selected_tab = self.tab_control.select()
        else:
            selected_tab = event.widget.select()
        if self.last_tab:
            for name, tab_data in self.tabs.items():
                if str(tab_data['frame']) == str(self.last_tab):
                    tab_data['current_page'] = self.current_page
                    tab_data['zoom'] = self.zoom
                    tab_data['scroll'] = self.canvas.yview()[0]
                    break

        for name, tab_data in self.tabs.items():
            if str(tab_data['frame']) == str(selected_tab):
                self.active_tab_data = tab_data
                self.pdf_path = tab_data['pdf_path']
                self.current_doc = tab_data['doc']
                self.current_page = tab_data['current_page']
                self.zoom = tab_data['zoom']
                self.page_count = len(self.current_doc)
                self.load_page_image()
                scroll_value = tab_data.get('scroll', 0.0)
                # Restore scroll position when switching tabs
                self.show_page(restore_scroll=scroll_value if scroll_value > 0 else None)
                break

        self.last_tab = selected_tab

    def close_tab(self, index):
        tab = self.tab_control.tabs()[index]
        for name in list(self.tabs.keys()):
            if str(self.tabs[name]['frame']) == tab:
                self.tabs[name]['doc'].close()
                del self.tabs[name]
                break
        self.tab_control.forget(index)
        if not self.tabs:
            # No more tabs - clear everything
            self.pdf_path = None
            self.current_doc = None
            self.current_image = None
            self.active_tab_data = None
            self.page_count = 0
            self.current_page = 0
            # Clear canvas but keep image_container for future use
            self.canvas.delete("all")
            self.image_container = self.canvas.create_image(0, 0, anchor='n')
            self.root.title("BareReader")
        else:
            # Switch to another tab if available
            remaining_tabs = self.tab_control.tabs()
            if remaining_tabs:
                # Select the first remaining tab or the one before the closed one
                new_index = min(index, len(remaining_tabs) - 1)
                self.tab_control.select(remaining_tabs[new_index])
                # Trigger tab change to update display
                self.on_tab_change(None)

    def confirm_close_current_tab(self):
        current_tab = self.tab_control.select()
        if not current_tab:
            return
        for name, tab_data in list(self.tabs.items()):
            if str(tab_data['frame']) == str(current_tab):
                confirm = messagebox.askyesno("Close Tab", f"Do you want to close '{name}'?")
                if confirm:
                    index = self.tab_control.index(current_tab)
                    self.close_tab(index)
                return

    def fit_to_width(self):
        self.load_page_image()
        # Restore scroll if available
        scroll_value = self.active_tab_data.get('scroll', 0.0) if self.active_tab_data else 0.0
        self.show_page(restore_scroll=scroll_value if scroll_value > 0 else None)

    def load_page_image(self):
        if self.current_doc:
            try:
                page = self.current_doc.load_page(self.current_page)
                # Create matrix for zoom
                mat = fitz.Matrix(self.zoom, self.zoom)
                
                # Render page
                pix = page.get_pixmap(matrix=mat)
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Apply dark mode inversion if enabled
                if self.dark_mode:
                    # Invert colors: white becomes black, black becomes white
                    image = ImageOps.invert(image)
                    # Optional: adjust brightness/contrast for better readability
                    enhancer = ImageEnhance.Brightness(image)
                    image = enhancer.enhance(0.95)  # Slightly dim to reduce eye strain
                
                self.current_image = image
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load page.\n\n{e}")

    def show_page(self, restore_scroll=None):
        if self.current_image:
            # Ensure image_container exists
            try:
                self.canvas.itemconfig(self.image_container, image="")
            except:
                # If it doesn't exist, create it
                self.image_container = self.canvas.create_image(0, 0, anchor='n')
            
            target_width = int(self.current_image.width)
            target_height = int(self.current_image.height)
            resized = self.current_image.resize((target_width, target_height), Image.LANCZOS)
            img = ImageTk.PhotoImage(resized)
            self.canvas.image = img
            self.canvas.itemconfig(self.image_container, image=img)
            canvas_width = self.canvas.winfo_width()
            if canvas_width <= 1:
                canvas_width = self.root.winfo_width() - 50  # Fallback width
            x = canvas_width // 2
            y = 0
            self.canvas.coords(self.image_container, x, y)
            self.canvas.config(scrollregion=(0, 0, max(canvas_width, target_width), max(target_height, self.canvas.winfo_height())))
            
            # Always start from top unless restoring a saved scroll position
            if restore_scroll is None:
                self.canvas.yview_moveto(0)
            else:
                self.root.after(50, lambda: self.canvas.yview_moveto(restore_scroll))
            
            # Update title and status
            title_text = f"BareReader - Página {self.current_page + 1} de {self.page_count} - Zoom {int(self.zoom * 100)}%"
            self.root.title(title_text)

    def next_page(self, event=None):
        if self.current_page < self.page_count - 1:
            self.current_page += 1
            self.load_page_image()
            # Always start from top when changing pages
            self.show_page(restore_scroll=None)

    def prev_page(self, event=None):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_page_image()
            # Always start from top when changing pages
            self.show_page(restore_scroll=None)

    def scroll_down(self, event=None):
        if self.canvas.yview()[1] >= 1.0 and self.current_page < self.page_count - 1:
            self.next_page()
        else:
            # Smoother scrolling
            self.canvas.yview_scroll(3, "units")

    def scroll_up(self, event=None):
        if self.canvas.yview()[0] <= 0.0 and self.current_page > 0:
            self.prev_page()
        else:
            # Smoother scrolling
            self.canvas.yview_scroll(-3, "units")

    def on_mouse_scroll(self, event):
        if event.num == 4 or event.delta > 0:
            self.scroll_up()
        elif event.num == 5 or event.delta < 0:
            self.scroll_down()
    
    def on_canvas_scroll(self, event):
        """Handle mouse wheel scrolling on canvas for smoother scrolling."""
        if event.num == 4 or event.delta > 0:
            # Scroll up
            if self.canvas.yview()[0] <= 0.0 and self.current_page > 0:
                self.prev_page()
            else:
                # Smooth scroll
                self.canvas.yview_scroll(-3, "units")
        elif event.num == 5 or event.delta < 0:
            # Scroll down
            if self.canvas.yview()[1] >= 1.0 and self.current_page < self.page_count - 1:
                self.next_page()
            else:
                # Smooth scroll
                self.canvas.yview_scroll(3, "units")

    def on_mouse_press(self, event):
        # Convert to canvas coordinates
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.selection_start = (x, y)
        self.selection_end = None
        self.redraw_selection()

    def on_mouse_drag(self, event):
        if self.selection_start:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            self.selection_end = (x, y)
            self.redraw_selection()

    def on_mouse_release(self, event):
        if self.selection_start and self.selection_end:
            # Only copy if there's a meaningful selection (not just a click)
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            if abs(x2 - x1) > 5 or abs(y2 - y1) > 5:  # Minimum selection size
                if self.copy_selection_to_clipboard():
                    messagebox.showinfo("Success", "Text copied to clipboard!")
                else:
                    messagebox.showwarning("No text", "Could not extract any text from the selection.")
            self.clear_selection()

    def flash_selection(self, color):
        """Flash the selection box with specified color."""
        for _ in range(2):
            self.canvas.itemconfig("selection", outline=color)
            self.canvas.update()
            time.sleep(0.1)
            self.canvas.itemconfig("selection", outline="red")
            self.canvas.update()
            time.sleep(0.1)
        self.clear_selection()

    def clear_selection(self):
        """Clear the selection visually."""
        self.canvas.delete("selection")
        self.selection_start = None
        self.selection_end = None
    
    def redraw_selection(self):
        """Redraw the selection rectangle."""
        if self.selection_start and self.selection_end:
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            self.canvas.delete("selection")  # Delete the previous rectangle
            # Create a more visible selection with semi-transparent fill
            selection_color = "lightblue" if not self.dark_mode else "darkblue"
            outline_color = "blue" if not self.dark_mode else "cyan"
            self.canvas.create_rectangle(
                x1, y1, x2, y2, 
                outline=outline_color, 
                width=2, 
                fill=selection_color,
                stipple="gray50",  # Semi-transparent pattern
                tags="selection"
            )

    def copy_selection_to_clipboard(self):
        """Copy selected text to clipboard based on selection box in PDF."""
        if not (self.selection_start and self.selection_end):
            return False

        try:
            page = self.current_doc.load_page(self.current_page)

            # Get actual image size from the pixmap
            pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom))
            pix_width, pix_height = pix.width, pix.height

            # Get canvas coordinates
            x1_canvas, y1_canvas = self.selection_start
            x2_canvas, y2_canvas = self.selection_end
            x1_canvas, x2_canvas = sorted([x1_canvas, x2_canvas])
            y1_canvas, y2_canvas = sorted([y1_canvas, y2_canvas])

            # Get the image position in the canvas
            img_x, img_y = self.canvas.coords(self.image_container)
            displayed_image = self.canvas.image  # ImageTk.PhotoImage
            disp_width = displayed_image.width()
            disp_height = displayed_image.height()

            # Compute offsets from the image position
            x1_rel = (x1_canvas - img_x + disp_width / 2) / disp_width
            y1_rel = (y1_canvas - img_y) / disp_height
            x2_rel = (x2_canvas - img_x + disp_width / 2) / disp_width
            y2_rel = (y2_canvas - img_y) / disp_height

            # Convert to PDF coordinates
            x1_pdf = x1_rel * pix_width / self.zoom
            y1_pdf = y1_rel * pix_height / self.zoom
            x2_pdf = x2_rel * pix_width / self.zoom
            y2_pdf = y2_rel * pix_height / self.zoom

            rect = fitz.Rect(x1_pdf, y1_pdf, x2_pdf, y2_pdf)

            text = page.get_textbox(rect)

            if text.strip():
                pyperclip.copy(text.strip())
                return True
            else:
                return False

        except Exception as e:
            print(f"Error copying text: {e}")
            return False


    def zoom_in(self):
        self.zoom += 0.1
        self.load_page_image()
        # Keep current scroll position when zooming
        current_scroll = self.canvas.yview()[0] if self.canvas.yview() else 0.0
        self.show_page(restore_scroll=current_scroll if current_scroll > 0 else None)

    def zoom_out(self):
        if self.zoom > 0.2:  # Prevent zoom from getting too small
            self.zoom -= 0.1
            self.load_page_image()
            # Keep current scroll position when zooming
            current_scroll = self.canvas.yview()[0] if self.canvas.yview() else 0.0
            self.show_page(restore_scroll=current_scroll if current_scroll > 0 else None)

    def go_to_page(self):
        try:
            page = int(self.page_entry.get()) - 1
            if 0 <= page < self.page_count:
                self.current_page = page
                self.load_page_image()
                # Always start from top when jumping to a page
                self.show_page(restore_scroll=None)
        except ValueError:
            pass

    def setup_button_styles(self):
        """Setup modern button styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Primary button style
        style.configure('Modern.TButton',
                      font=('Segoe UI', 9),
                      padding=8,
                      relief='flat',
                      borderwidth=0)
        
        style.map('Modern.TButton',
                 background=[('active', self.colors['accent_hover']),
                           ('!active', self.colors['accent'])],
                 foreground=[('active', 'white'),
                           ('!active', 'white')])
        
        # Danger button style
        style.configure('Danger.TButton',
                      font=('Segoe UI', 9),
                      padding=8,
                      relief='flat',
                      borderwidth=0)
        
        style.map('Danger.TButton',
                 background=[('active', '#c0392b'),
                           ('!active', self.colors['danger'])],
                 foreground=[('active', 'white'),
                           ('!active', 'white')])
        
        # Small button style
        style.configure('Small.TButton',
                      font=('Segoe UI', 8),
                      padding=4,
                      relief='flat',
                      borderwidth=0)
        
        style.map('Small.TButton',
                 background=[('active', self.colors['accent_hover']),
                           ('!active', self.colors['accent'])],
                 foreground=[('active', 'white'),
                           ('!active', 'white')])
    
    def create_modern_button(self, parent, text, command, tooltip=None, color='primary', size='normal'):
        """Create a modern styled button with tooltip - all buttons same width"""
        style_name = f'{color.capitalize()}.TButton' if color != 'primary' else 'Modern.TButton'
        # All buttons use the same style and width for consistency
        if size == 'small':
            style_name = 'Modern.TButton'  # Use same style for all
        
        btn = ttk.Button(parent, text=text, command=command, style=style_name, width=14)
        btn.pack(side="left", padx=3)
        
        if tooltip:
            ToolTip(btn, tooltip)
        
        return btn
    
    def apply_dark_mode(self):
        """Apply dark mode theme to the interface"""
        if self.dark_mode:
            # Dark mode colors
            bg_color = self.colors['dark_bg']
            toolbar_bg = self.colors['dark_toolbar']
            fg_color = self.colors['dark_fg']
            canvas_bg = "#0a0a0a"
            border_color = self.colors['dark_border']
        else:
            # Light mode colors
            bg_color = self.colors['bg']
            toolbar_bg = self.colors['toolbar_bg']
            fg_color = self.colors['fg']
            canvas_bg = "#ffffff"
            border_color = self.colors['border']
        
        # Update root and frames
        self.root.configure(bg=bg_color)
        self.canvas.configure(bg=canvas_bg)
        
        # Update toolbar
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame):
                try:
                    widget.configure(bg=toolbar_bg if 'toolbar' in str(widget) else bg_color)
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Frame):
                            child.configure(bg=toolbar_bg)
                        elif isinstance(child, tk.Label):
                            child.configure(bg=toolbar_bg, fg=fg_color)
                        elif isinstance(child, tk.Entry):
                            child.configure(bg='white' if not self.dark_mode else '#2d2d2d',
                                          fg=fg_color,
                                          highlightbackground=border_color,
                                          highlightcolor=self.colors['accent'])
                except:
                    pass
        
        # Update button text
        if hasattr(self, 'btn_dark'):
            self.btn_dark.config(text="☀️ Claro" if self.dark_mode else "🌙 Oscuro")
    
    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.apply_dark_mode()
        
        # Reload current page with new dark mode setting
        if self.current_doc:
            self.load_page_image()
            # Keep current scroll position when toggling dark mode
            current_scroll = self.canvas.yview()[0] if self.canvas.yview() else 0.0
            self.show_page(restore_scroll=current_scroll if current_scroll > 0 else None)

root = tk.Tk()
viewer = PDFViewer(root)
root.mainloop()