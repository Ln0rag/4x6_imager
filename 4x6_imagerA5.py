import sys
import os
import subprocess

def check_dependencies():
    missing_pip = []
    
    try:
        import PIL
    except ImportError:
        missing_pip.append("Pillow")
    
    try:
        import rembg
    except ImportError:
        missing_pip.append("rembg[cpu]")

    try:
        import cv2
    except ImportError:
        missing_pip.append("opencv-python")

    try:
        import numpy
    except ImportError:
        missing_pip.append("numpy")

    if missing_pip:
        print(f"[Installer] Missing packages: {missing_pip}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing_pip, "--break-system-packages"])
        print("[Installer] Packages installed. Restarting script...")
        os.execv(sys.executable, ['python3'] + sys.argv)
        
    try:
        import tkinter
    except ImportError:
        print("[Installer] Missing tkinter. Installing...")
        os.system("sudo apt-get update && sudo apt-get install -y python3-tk")
        os.execv(sys.executable, ['python3'] + sys.argv)

    try:
        from rembg import new_session
        print("[Installer] Checking rembg model: u2net_human_seg...")
        _ = new_session("u2net_human_seg")
        print("[Installer] Model u2net_human_seg ready.")
    except Exception as e:
        print(f"[Installer] Warning: Could not preload rembg model: {e}")

check_dependencies()

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageEnhance
from rembg import remove, new_session
import datetime
import cv2
import numpy as np

class ImageCropper:
    def __init__(self, root):
        self.root = root
        self.root.title("Pro Studio - AI Photo Lab (A5: 8 Photos)")
        self.target_ratio = 40 / 60 
        self.layout_mode = "a5"
        
        self.filepath = filedialog.askopenfilename(
            title="Select Client Image", 
            filetypes=[("Images", "*.jpg *.png *.jpeg *.webp *.bmp")]
        )
        if not self.filepath:
            root.destroy()
            return
            
        self.original_image = Image.open(self.filepath)
        
        max_display_size = 800
        orig_w, orig_h = self.original_image.size
        
        if orig_w > orig_h:
            self.display_width = max_display_size
            self.display_height = int(max_display_size * (orig_h / orig_w))
        else:
            self.display_height = max_display_size
            self.display_width = int(max_display_size * (orig_w / orig_h))
            
        self.display_image = self.original_image.resize((self.display_width, self.display_height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.display_image)
        
        self.canvas = tk.Canvas(root, width=self.display_width, height=self.display_height, cursor="cross")
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        
        self.rect = None
        self.start_x = None
        self.start_y = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)
        
        mode_text = "A5 Sheet (8 Photos, 40x60 mm each)"
        tk.Label(btn_frame, text=f"Layout: {mode_text}", font=("Arial", 10), fg="gray").pack()
        
        tk.Button(
            btn_frame, 
            text="Confirm Crop & Start AI Engine (6 Models)", 
            command=self.process_image, 
            bg="green", 
            fg="white", 
            font=("Arial", 14, "bold")
        ).pack(pady=5)
        
    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=3)

    def on_drag(self, event):
        cur_x = event.x
        if cur_x > self.display_width: cur_x = self.display_width
        if cur_x < 0: cur_x = 0
        width = cur_x - self.start_x
        height = width / self.target_ratio
        
        if self.start_y + height > self.display_height:
            height = self.display_height - self.start_y
            width = height * self.target_ratio
            
        self.canvas.coords(self.rect, self.start_x, self.start_y, self.start_x + width, self.start_y + height)

    def on_release(self, event):
        pass

    def mm_to_px(self, mm, dpi=300):
        return int(mm * dpi / 25.4)

    def apply_beauty_filter(self, pil_img):
        pil_img = pil_img.convert("RGB")
        cv_img = np.array(pil_img)
        cv_img = cv_img[:, :, ::-1].copy()
        
        smoothed = cv2.bilateralFilter(cv_img, d=11, sigmaColor=60, sigmaSpace=60)
        natural_beauty = cv2.addWeighted(smoothed, 0.7, cv_img, 0.3, 0)
        
        beauty_rgb = cv2.cvtColor(natural_beauty, cv2.COLOR_BGR2RGB)
        return Image.fromarray(beauty_rgb)

    def show_preview_window(self, original, beautified):
        self.preview_win = tk.Toplevel(self.root)
        self.preview_win.title("Step 1: Face Beauty Settings")
        self.preview_win.grab_set()

        disp_h = 400
        ratio = disp_h / original.height
        disp_w = int(original.width * ratio)

        orig_disp = ImageTk.PhotoImage(original.resize((disp_w, disp_h), Image.Resampling.LANCZOS))
        beau_disp = ImageTk.PhotoImage(beautified.resize((disp_w, disp_h), Image.Resampling.LANCZOS))

        frame = tk.Frame(self.preview_win)
        frame.pack(padx=20, pady=20)

        lbl_orig = tk.Label(frame, image=orig_disp, text="Original Face", compound="top", font=("Arial", 12, "bold"))
        lbl_orig.image = orig_disp
        lbl_orig.grid(row=0, column=0, padx=10)

        lbl_beau = tk.Label(frame, image=beau_disp, text="Auto Beauty Filter", compound="top", font=("Arial", 12, "bold"))
        lbl_beau.image = beau_disp
        lbl_beau.grid(row=0, column=1, padx=10)

        self.chosen_image = original

        def choose_orig():
            self.chosen_image = original
            self.preview_win.destroy()

        def choose_beau():
            self.chosen_image = beautified
            self.preview_win.destroy()

        btn_frame = tk.Frame(self.preview_win)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Keep Original", command=choose_orig, bg="#d9534f", fg="white", font=("Arial", 12, "bold"), width=15).pack(side="left", padx=20)
        tk.Button(btn_frame, text="Apply Beauty", command=choose_beau, bg="#5cb85c", fg="white", font=("Arial", 12, "bold"), width=15).pack(side="right", padx=20)

        self.root.wait_window(self.preview_win)

    def show_six_model_preview(self, variations):
        self.multi_win = tk.Toplevel(self.root)
        self.multi_win.title("Step 2: Choose The Best Edge Morphology (6 Models)")
        self.multi_win.grab_set()

        container = tk.Frame(self.multi_win)
        container.pack(padx=10, pady=10)

        self.chosen_bg_rgba = variations[0][1] 

        row_idx = 0
        col_idx = 0
        for title, rgba_img in variations:
            disp_w = 280
            ratio = disp_w / rgba_img.width
            disp_h = int(rgba_img.height * ratio)
            
            white_bg = Image.new("RGB", rgba_img.size, (255, 255, 255))
            white_bg.paste(rgba_img, mask=rgba_img.split()[3])
            
            preview_img = ImageTk.PhotoImage(white_bg.resize((disp_w, disp_h), Image.Resampling.LANCZOS))
            
            frame = tk.Frame(container, bd=2, relief="groove")
            frame.grid(row=row_idx, column=col_idx, padx=10, pady=10)
            
            lbl = tk.Label(frame, image=preview_img)
            lbl.image = preview_img
            lbl.pack()
            
            def make_choice(selected_rgba=rgba_img):
                self.chosen_bg_rgba = selected_rgba
                self.multi_win.destroy()
                
            btn = tk.Button(frame, text=title, command=make_choice, bg="#007bff", fg="white", font=("Arial", 10, "bold"))
            btn.pack(pady=8, fill="x", padx=8)
            
            col_idx += 1
            if col_idx >= 3:
                col_idx = 0
                row_idx += 1

        self.root.wait_window(self.multi_win)

    def build_cell_image(self, bg_removed):
        """Build a single cell (40x60 photo + date)"""
        white_bg = Image.new("RGB", bg_removed.size, (255, 255, 255))
        white_bg.paste(bg_removed, mask=bg_removed.split()[3])
        
        s_w, s_h = self.mm_to_px(40), self.mm_to_px(60)
        final_photo_small = white_bg.resize((s_w, s_h), Image.Resampling.LANCZOS)
        
        draw_small = ImageDraw.Draw(final_photo_small)
        draw_small.rectangle([0, 0, s_w - 1, s_h - 1], outline="black", width=self.mm_to_px(0.5))
        
        cell_w = s_w
        cell_h = s_h + self.mm_to_px(8)
        cell_img = Image.new("RGB", (cell_w, cell_h), (255, 255, 255))
        cell_img.paste(final_photo_small, (0, 0))
        
        date_str = datetime.datetime.now().strftime("%d-%m-%Y")
        try: 
            font = ImageFont.truetype("DejaVuSans.ttf", 35)
        except IOError: 
            font = ImageFont.load_default()
            
        draw_cell = ImageDraw.Draw(cell_img)
        draw_cell.text((0, s_h + self.mm_to_px(2)), date_str, fill="black", font=font)
        
        return cell_img, cell_w, cell_h

    def build_a5_layout(self, cell_img, cell_w, cell_h):
        """A5 landscape (210x148 mm) = half of an A4 sheet: 8 photos (4x2), real 40x60 size"""
        w, h = self.mm_to_px(210), self.mm_to_px(148)
        sheet = Image.new("RGB", (w, h), (255, 255, 255))
        
        margin_x = self.mm_to_px(10)
        margin_y = self.mm_to_px(4)
        cols, rows = 4, 2
        gap_x = (w - 2 * margin_x - cols * cell_w) / (cols - 1)
        gap_y = (h - 2 * margin_y - rows * cell_h) / (rows - 1)
        
        for row in range(rows):
            for col in range(cols):
                x = margin_x + col * (cell_w + gap_x)
                y = margin_y + row * (cell_h + gap_y)
                sheet.paste(cell_img, (int(x), int(y)))
        return sheet

    def process_image(self):
        if not self.rect:
            messagebox.showerror("Error", "Please select the crop area.")
            return
            
        coords = self.canvas.coords(self.rect)
        if not coords or len(coords) < 4:
            return
            
        scale_x = self.original_image.size[0] / self.display_width
        scale_y = self.original_image.size[1] / self.display_height
        crop_box = (int(coords[0] * scale_x), int(coords[1] * scale_y), int(coords[2] * scale_x), int(coords[3] * scale_y))
        
        cropped_high_res = self.original_image.crop(crop_box)
        cropped_high_res = cropped_high_res.convert("RGB")
        
        self.root.title("Generating Face Beauty Preview...")
        self.root.update()
        beautified_image = self.apply_beauty_filter(cropped_high_res)
        
        self.show_preview_window(cropped_high_res, beautified_image)
        final_selected_image = self.chosen_image
        
        self.root.title("Processing 6 Edge Models... Please wait")
        self.root.update()
        
        variations = []
        
        try:
            session = new_session("u2net_human_seg")
            
            # ============================================================
            # 3 RMBG Degree Variations (Light / Medium / Heavy)
            # ============================================================
            
            raw_rgba_light = remove(
                final_selected_image, 
                session=session, 
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=5
            ).convert("RGBA")
            variations.append(("Option 4: Light AI Edge\n(Subtle matting)", raw_rgba_light))
            
            raw_rgba_medium = remove(
                final_selected_image,
                session=session,
                alpha_matting=True,
                alpha_matting_foreground_threshold=220,
                alpha_matting_background_threshold=20,
                alpha_matting_erode_size=10
            ).convert("RGBA")
            variations.append(("Option 5: Medium AI Edge\n(Balanced matting)", raw_rgba_medium))
            
            raw_rgba_heavy = remove(
                final_selected_image,
                session=session,
                alpha_matting=True,
                alpha_matting_foreground_threshold=200,
                alpha_matting_background_threshold=30,
                alpha_matting_erode_size=15
            ).convert("RGBA")
            variations.append(("Option 6: Heavy AI Edge\n(Aggressive matting)", raw_rgba_heavy))
            
            # ============================================================
            # ORIGINAL: 3 Edge Morphology Variations (Raw / Crisp / Soft)
            # ============================================================
            
            raw_rgba = remove(final_selected_image, session=session, alpha_matting=False).convert("RGBA")
            variations.append(("Option 1: Raw AI\n(Best for clean backgrounds)", raw_rgba))
            
            r, g, b, alpha_mask = raw_rgba.split()
            mask_np = np.array(alpha_mask)
            
            kernel_erode = np.ones((5, 5), np.uint8)
            trimmed_mask_np = cv2.erode(mask_np, kernel_erode, iterations=1)
            
            trimmed_rgba = final_selected_image.convert("RGBA").copy()
            trimmed_rgba.putalpha(Image.fromarray(trimmed_mask_np))
            variations.append(("Option 2: Crisp Edge Trim\n(Eats away tree halos)", trimmed_rgba))
            
            feathered_mask_np = cv2.GaussianBlur(trimmed_mask_np, (7, 7), 0)
            
            feathered_rgba = final_selected_image.convert("RGBA").copy()
            feathered_rgba.putalpha(Image.fromarray(feathered_mask_np))
            variations.append(("Option 3: Soft Studio Edge\n(Best for natural blend)", feathered_rgba))
            
        except Exception as e:
            messagebox.showerror("AI Engine Error", f"Background removal failed:\n{str(e)}")
            print(f"Error: {e}")
            return

        self.root.title("Awaiting Your Choice...")
        self.show_six_model_preview(variations)
        bg_removed = self.chosen_bg_rgba
        
        self.root.title("Generating Final A5 PDF...")
        self.root.update()

        # Build the cell image (40x60 + date)
        cell_img, cell_w, cell_h = self.build_cell_image(bg_removed)
        
        a5_sheet = self.build_a5_layout(cell_img, cell_w, cell_h)
        
        save_path = os.path.join(os.path.dirname(self.filepath), "Print_Ready_A5.pdf")
        a5_sheet.save(save_path, "PDF", resolution=300)
        
        messagebox.showinfo("Success", f"Processing completed successfully!\nA5 sheet (8 photos)\nPDF saved at:\n{save_path}")
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCropper(root)
    root.mainloop()
