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
        toolbar.add_widget(Button(text='Open PDF', on_press=self.open_pdf))
        toolbar.add_widget(Button(text='<< Prev', on_press=self.prev_page))
        toolbar.add_widget(Button(text='Next >>', on_press=self.next_page))
        toolbar.add_widget(Button(text='Zoom +', on_press=self.zoom_in))
        toolbar.add_widget(Button(text='Zoom -', on_press=self.zoom_out))
        self.page_input = TextInput(text='1', multiline=False, size_hint_x=None, width=80)
        toolbar.add_widget(self.page_input)
        toolbar.add_widget(Button(text='Go', on_press=self.go_to_page))
        self.add_widget(toolbar)

        # Scrollable image viewer
        self.scroll = ScrollView(do_scroll_x=False)
        self.image_widget = Image(allow_stretch=True, keep_ratio=True, size_hint_y=None)
        self.scroll.add_widget(self.image_widget)
        self.add_widget(self.scroll)

        Window.bind(on_key_down=self.on_key_down)

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

            # 🔄 Corregir espejado: flip horizontal
            image = image.transpose(PILImage.FLIP_LEFT_RIGHT)

            texture = self.pil_to_texture(image)
            self.image_widget.texture = texture
            self.image_widget.height = texture.height
            self.page_input.text = str(self.current_page + 1)
        except Exception as e:
            self.show_popup(f"Error loading page: {e}")

    def pil_to_texture(self, image):
        tex = Texture.create(size=image.size, colorfmt='rgb')
        tex.blit_buffer(image.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        return tex

    def next_page(self, instance=None):
        if self.current_page < self.page_count - 1:
            self.current_page += 1
            self.load_page()

    def prev_page(self, instance=None):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_page()

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

    def on_key_down(self, window, key, scancode, codepoint, modifier):
        if key == 273:  # Up
            self.prev_page()
        elif key == 274:  # Down
            self.next_page()

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