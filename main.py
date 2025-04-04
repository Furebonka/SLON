import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import imageio
import sys

def get_folder_size(folder):
    total_size = 0
    for dirpath, _, filenames in os.walk(folder):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024)

def get_unique_folder(base_path):
    if not os.path.exists(base_path):
        return base_path
    counter = 2
    while True:
        new_path = f"{base_path} ({counter})"
        if not os.path.exists(new_path):
            return new_path
        counter += 1

def compress_single_image(image_path, output_folder, quality):
    os.makedirs(output_folder, exist_ok=True)
    try:
        img = Image.open(image_path)
        img = img.convert("RGB")
        output_path = os.path.join(output_folder, os.path.basename(image_path))
        img.save(output_path, quality=quality, optimize=True)
    except Exception as e:
        print(f"Ошибка сжатия изображения: {e}")

def compress_images_from_folder(input_folder, output_base_folder, quality, max_size_mb=19):
    os.makedirs(output_base_folder, exist_ok=True)
    folder_index = 0
    current_folder = output_base_folder

    for file_name in os.listdir(input_folder):
        file_path = os.path.join(input_folder, file_name)
        if os.path.isfile(file_path):
            try:
                # Обработка HEIC файлов
                if file_name.lower().endswith(".heic"):
                    try:
                        # Чтение HEIC файла с помощью imageio
                        img = imageio.imread(file_path)

                        # Преобразуем в формат, который понимает Pillow (например, JPEG)
                        temp_jpeg_path = os.path.splitext(file_path)[0] + ".jpg"

                        # Используем Pillow для сохранения с оптимизацией сжатием (JPEG)
                        img_pil = Image.fromarray(img)
                        img_pil.convert("RGB").save(temp_jpeg_path, format="JPEG", quality=quality, optimize=True)

                        # Теперь сжимаем изображение
                        compress_single_image(temp_jpeg_path, current_folder, quality)
                        os.remove(temp_jpeg_path)  # Удаляем временный JPEG после сжатия
                    except Exception as e:
                        print(f"Ошибка конвертации HEIC: {e}")

                # Для остальных файлов (JPEG, PNG)
                elif file_name.lower().endswith((".jpg", ".jpeg", ".png")):
                    compress_single_image(file_path, current_folder, quality)

                # Если размер папки превышает лимит, создаем новую
                if get_folder_size(current_folder) > max_size_mb:
                    folder_index += 1
                    current_folder = f"{output_base_folder}_{folder_index}"
                    os.makedirs(current_folder, exist_ok=True)

            except Exception as e:
                print(f"Ошибка обработки {file_name}: {e}")


def resource_path(relative_path):
    """Получает путь к встроенному ресурсу (картинке) при сборке приложения"""
    try:
        # Для PyInstaller
        if getattr(sys, 'frozen', False):
            # Если приложение собрано с помощью PyInstaller
            base_path = sys._MEIPASS
        else:
            # Если приложение запущено как исходный код
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
    except Exception as e:
        print(f"Ошибка при получении пути к ресурсу: {e}")
        return relative_path

class ElephantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SLON")
        self.root.geometry("400x350")
        self.root.resizable(False, False)

        icon_path = os.path.join(os.path.dirname(__file__), "elephant.ico")
        self.root.iconbitmap(icon_path)
        self.selected_path = None
        self.mode = None  # 'single' или 'folder'
        self.temp_output = os.path.join(os.path.abspath(os.curdir), "temp_slon_output")

        self.setup_ui()

    def setup_ui(self):
        self.root.configure(bg="#ffffff")

        self.style_btn = {
            "font": ("Segoe UI", 11),
            "bg": "#f2f2f2",
            "fg": "#333",
            "activebackground": "#dddddd",
            "activeforeground": "#000",
            "bd": 0,
            "relief": "flat",
            "width": 25,
            "padx": 10,
            "pady": 8,
        }

        tk.Button(self.root, text="📷 Указать фото", command=self.select_single_image, **self.style_btn).pack(pady=(30, 10))
        tk.Button(self.root, text="📁 Указать папку", command=self.select_folder, **self.style_btn).pack(pady=10)

        self.download_btn = tk.Button(self.root, text="⬇️ Скачать сжатое", command=self.compress_and_download, state="disabled", **self.style_btn)
        self.download_btn.pack(pady=10)

        # Ползунок
        tk.Label(
            self.root,
            text="Степень сжатия (больше = хуже качество)\nРекомендуется: 30–70%",
            font=("Segoe UI", 9),
            bg="#ffffff",
            fg="#444",
            justify="center"
        ).pack(pady=(20, 5))

        self.quality_slider = tk.Scale(
            self.root,
            from_=10,
            to=95,
            orient="horizontal",
            bg="#ffffff",
            troughcolor="#e0e0e0",
            highlightthickness=0,
            sliderlength=15
        )
        self.quality_slider.set(50)
        self.quality_slider.pack()

    def enable_download(self):
        self.download_btn.config(state="normal")

    def select_single_image(self):
        path = filedialog.askopenfilename(filetypes=[("Изображения", "*.jpg *.jpeg *.png *.heic")])
        if path:
            self.selected_path = path
            self.mode = "single"
            self.enable_download()

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.selected_path = folder
            self.mode = "folder"
            self.enable_download()

    def compress_and_download(self):
        if not self.selected_path or not self.mode:
            return

        quality = 100 - self.quality_slider.get()
        shutil.rmtree(self.temp_output, ignore_errors=True)

        # Обработка одиночного изображения
        if self.mode == "single":
            # Если выбран файл HEIC, сначала конвертируем его в PNG
            if self.selected_path.lower().endswith(".heic"):
                try:
                    # Чтение HEIC файла с помощью imageio
                    img = imageio.imread(self.selected_path)

                    # Преобразуем в формат, который понимает Pillow (например, JPEG)
                    temp_jpeg_path = os.path.splitext(self.selected_path)[0] + ".jpg"

                    # Используем Pillow для сохранения с оптимизацией сжатием (JPEG)
                    img_pil = Image.fromarray(img)
                    img_pil.convert("RGB").save(temp_jpeg_path, format="JPEG", quality=quality, optimize=True)

                    # Теперь сжимаем изображение
                    compress_single_image(temp_jpeg_path, self.temp_output, quality)
                    os.remove(temp_jpeg_path)  # Удаляем временный JPEG после сжатия
                except Exception as e:
                    print(f"Ошибка конвертации HEIC: {e}")


            else:
                compress_single_image(self.selected_path, self.temp_output, quality)

        # Обработка папки с изображениями
        elif self.mode == "folder":
            compress_images_from_folder(self.selected_path, self.temp_output, quality)

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        target = get_unique_folder(os.path.join(desktop, "сжатое"))
        shutil.copytree(self.temp_output, target)

        shutil.rmtree(self.temp_output, ignore_errors=True)
        messagebox.showinfo("Готово", f"Файлы сохранены на рабочем столе:\n{target}")
        self.reset_state()

    def reset_state(self):
        self.selected_path = None
        self.mode = None
        self.download_btn.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = ElephantApp(root)
    root.mainloop()
