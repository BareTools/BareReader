# barereader_kivy/main.py

import os
import fitz  # PyMuPDF
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from PIL import Image as PILImage
from kivy.uix.popup import Popup
from kivy.clock import Clock

class PDFViewer(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)

        self.pdf_path = None
        self.current_doc = None
        self.current_page = 0
        self.page_count = 0
        self.zoom = 1.5

        # Toolbar
        toolbar = BoxLayout(size_hint_y=None, height=50)
        toolbar.add_widget(Button(text='Open', on_press=self.open_pdf))
        # toolbar.add_widget(Button(text='<< Prev', on_press=self.prev_page))
        # toolbar.add_widget(Button(text='Next >>', on_press=self.next_page))
        toolbar.add_widget(Button(text='Zoom +', on_press=self.zoom_in))
        toolbar.add_widget(Button(text='Zoom -', on_press=self.zoom_out))
        self.page_input = TextInput(text='1', multiline=False, size_hint_x=None, width=80)
        toolbar.add_widget(self.page_input)
        toolbar.add_widget(Button(text='Go', on_press=self.go_to_page))
        self.add_widget(toolbar)

        # Scrollable image viewer
        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        self.image_widget = Image(size_hint_y=None)
        self.scroll.add_widget(self.image_widget)
        self.add_widget(self.scroll)

        # self.scroll.bind(on_scroll_y=self.check_scroll_position)

        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_scroll=self.on_scroll)

    def update_title(self):
        if self.current_doc:
            App.get_running_app().title = f"BareReader - Page {self.current_page + 1} of {self.page_count} - Zoom {int(self.zoom * 100)}%"
        else:
            App.get_running_app().title = "BareReader"

    def open_pdf(self, instance):
        from kivy.utils import platform
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE])

        from plyer import filechooser
        filechooser.open_file(on_selection=self.load_pdf)

    def load_pdf(self, selection):
        if not selection:
            return

        self.pdf_path = selection[0]
        try:
            self.current_doc = fitz.open(self.pdf_path)
            self.page_count = len(self.current_doc)
            self.current_page = 0
            self.load_page()
        except Exception as e:
            self.show_popup(f"Failed to open PDF: {e}")

    def load_page(self):
        if not self.current_doc:
            return

        try:
            page = self.current_doc.load_page(self.current_page)
            mat = fitz.Matrix(self.zoom, self.zoom).prerotate(180)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            image = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
            image = image.transpose(PILImage.FLIP_LEFT_RIGHT)

            texture = self.pil_to_texture(image)
            self.image_widget.texture = texture
            self.image_widget.size_hint_y = None
            self.image_widget.height = texture.height
            self.page_input.text = str(self.current_page + 1)
            self.update_title()

            Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 1))
        except Exception as e:
            self.show_popup(f"Error loading page: {e}")

    def pil_to_texture(self, image):
        tex = Texture.create(size=image.size, colorfmt='rgb')
        tex.blit_buffer(image.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        return tex

    def scroll_down(self):
        if self.scroll.scroll_y > 0.0:
            self.scroll.scroll_y = max(0.0, self.scroll.scroll_y - 0.1)
        elif self.current_page < self.page_count - 1:
            self.current_page += 1
            self.load_page()

    def scroll_up(self):
        if self.scroll.scroll_y < 1.0:
            self.scroll.scroll_y = min(1.0, self.scroll.scroll_y + 0.1)
        elif self.current_page > 0:
            self.current_page -= 1
            self.load_page()

    def next_page(self, instance=None):
        self.scroll_down()

    def prev_page(self, instance=None):
        self.scroll_up()

    def zoom_in(self, instance):
        self.zoom += 0.1
        self.load_page()

    def zoom_out(self, instance):
        if self.zoom > 0.2:
            self.zoom -= 0.1
            self.load_page()

    def go_to_page(self, instance):
        try:
            page = int(self.page_input.text.strip()) - 1
            if 0 <= page < self.page_count:
                self.current_page = page
                self.load_page()
        except:
            pass

    def on_key_down(self, window, key, scancode, codepoint, modifiers):
        if key == 273:  # Up
            self.scroll_up()
        elif key == 274:  # Down
            self.scroll_down()

    def on_scroll(self, window, scroll_x, scroll_y, x, y):
        if scroll_y < 0:
            self.scroll_down()
        elif scroll_y > 0:
            self.scroll_up()
        elif scroll_y > 0:
            if self.scroll.scroll_y < 1.0:
                self.scroll.scroll_y = min(1.0, self.scroll.scroll_y + 0.1)
            elif self.current_page > 0:
                self.current_page -= 1
                self.load_page()

    def show_popup(self, message):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text=message))
        popup = Popup(title='Error', content=content, size_hint=(None, None), size=(400, 200))
        popup.open()

class BareReaderApp(App):
    def build(self):
        return PDFViewer()

if __name__ == '__main__':
    BareReaderApp().run()
