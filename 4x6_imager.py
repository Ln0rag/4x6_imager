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
import math
import random
import cv2
import numpy as np

class ImageCropper:
    def __init__(self, root):
        self.root = root
        self.root.title("Pro Studio - AI Photo Lab (6 Edge Models)")
        self.target_ratio = 40 / 60 
        self.layout_mode = None  # "card" or "grid"
        
        self.filepath = filedialog.askopenfilename(
            title="Select Client Image", 
            filetypes=[("Images", "*.jpg *.png *.jpeg *.webp *.bmp")]
        )
        if not self.filepath:
            root.destroy()
            return
            
        self.original_image = Image.open(self.filepath)
        
        # ===== STEP 0: Choose Layout Style =====
        self.show_layout_selector()
        if self.layout_mode is None:
            root.destroy()
            return
        
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
        
        mode_text = "Card Mode" if self.layout_mode == "card" else "Grid Mode (16 Photos)"
        tk.Label(btn_frame, text=f"Layout: {mode_text}", font=("Arial", 10), fg="gray").pack()
        
        tk.Button(
            btn_frame, 
            text="Confirm Crop & Start AI Engine (6 Models)", 
            command=self.process_image, 
            bg="green", 
            fg="white", 
            font=("Arial", 14, "bold")
        ).pack(pady=5)
        
    def show_layout_selector(self):
        sel_win = tk.Toplevel(self.root)
        sel_win.title("Choose Print Layout")
        sel_win.grab_set()
        sel_win.transient(self.root)
        
        frame = tk.Frame(sel_win)
        frame.pack(padx=30, pady=30)
        
        tk.Label(frame, text="Select Your Print Layout", font=("Arial", 18, "bold")).pack(pady=(0, 20))
        
        def choose_card():
            self.layout_mode = "card"
            sel_win.destroy()
            
        def choose_grid():
            self.layout_mode = "grid"
            sel_win.destroy()
            
        def cancel():
            self.layout_mode = None
            sel_win.destroy()
        
        # Card style button
        card_frame = tk.Frame(frame, bd=2, relief="ridge", padx=15, pady=15)
        card_frame.pack(fill="x", pady=5)
        tk.Label(card_frame, text="Card Style", font=("Arial", 14, "bold"), fg="#007bff").pack()
        tk.Label(card_frame, text="1 Large Portrait Photo + 8 Small ID Photos", font=("Arial", 11)).pack(pady=5)
        tk.Button(card_frame, text="Select Card Style", command=choose_card, bg="#007bff", fg="white", font=("Arial", 12, "bold"), width=25).pack()
        
        # Grid style button
        grid_frame = tk.Frame(frame, bd=2, relief="ridge", padx=15, pady=15)
        grid_frame.pack(fill="x", pady=5)
        tk.Label(grid_frame, text="Grid Style", font=("Arial", 14, "bold"), fg="#28a745").pack()
        tk.Label(grid_frame, text="16 Small ID Photos Only (4x4 Grid on A4)", font=("Arial", 11)).pack(pady=5)
        tk.Button(grid_frame, text="Select Grid Style", command=choose_grid, bg="#28a745", fg="white", font=("Arial", 12, "bold"), width=25).pack()
        
        tk.Button(frame, text="Cancel", command=cancel, font=("Arial", 10), fg="red").pack(pady=(15, 0))
        
        self.root.wait_window(sel_win)
        
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

    def get_clothes_color(self, rgba_img):
        width, height = rgba_img.size
        bottom_part = rgba_img.crop((0, int(height * 0.75), width, height))
        pixels = bottom_part.load()
        
        r_total, g_total, b_total, count = 0, 0, 0, 0
        for x in range(width):
            for y in range(bottom_part.height):
                r, g, b, a = pixels[x, y]
                if a > 200:
                    r_total += r
                    g_total += g
                    b_total += b
                    count += 1
                    
        if count == 0: 
            return (50, 100, 150) 
        return (r_total // count, g_total // count, b_total // count)

    def generate_cheerful_background(self, W, H, base_color):
        r, g, b = base_color
        c_light = (min(255, r + 60), min(255, g + 60), min(255, b + 60))
        c_dark = (max(0, r - 40), max(0, g - 40), max(0, b - 40))
        c_accent = (min(255, r + 40), max(0, g - 20), min(255, b + 40)) 
        
        base = Image.new('RGB', (2, 2))
        base.putdata([c_light, base_color, base_color, c_dark])
        bg = base.resize((W, H), Image.Resampling.BICUBIC)
        
        overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        for _ in range(25):
            rad = random.randint(self.mm_to_px(5), self.mm_to_px(30))
            cx = random.randint(0, W)
            cy = random.randint(0, H)
            color_choice = random.choice([c_light, c_dark, c_accent, base_color])
            alpha = random.randint(30, 120) 
            draw.ellipse([cx-rad, cy-rad, cx+rad, cy+rad], fill=(*color_choice, alpha))
            
        bg.paste(overlay, (0, 0), overlay)
        return bg

    def draw_wavy_gold_border(self, draw, x0, y0, x1, y1):
        gold = (218, 165, 32)
        thickness = self.mm_to_px(1.2)
        freq = 0.05
        amp = self.mm_to_px(2.5)
        
        def draw_wave(start_pt, end_pt, is_horizontal):
            length = int(end_pt[0] - start_pt[0] if is_horizontal else end_pt[1] - start_pt[1])
            pts = []
            for i in range(length):
                wave = math.sin(i * freq) * amp
                px = start_pt[0] + i if is_horizontal else start_pt[0] + wave
                py = start_pt[1] + wave if is_horizontal else start_pt[1] + i
                pts.append((px, py))
            draw.line(pts, fill=gold, width=thickness)

        draw_wave((x0, y0), (x1, y0), True)
        draw_wave((x0, y1), (x1, y1), True)
        draw_wave((x0, y0), (x0, y1), False)
        draw_wave((x1, y0), (x1, y1), False)
        
        def draw_sun(cx, cy):
            r = self.mm_to_px(3)
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                ex = cx + math.cos(rad) * (r * 1.8)
                ey = cy + math.sin(rad) * (r * 1.8)
                draw.line([(cx, cy), (ex, ey)], fill=gold, width=self.mm_to_px(0.8))
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=gold)

        draw_sun(x0, y0)
        draw_sun(x1, y0)
        draw_sun(x0, y1)
        draw_sun(x1, y1)
        
        arc_r = self.mm_to_px(10)
        arc_pad = self.mm_to_px(5)
        draw.arc([x0+arc_pad, y0+arc_pad, x0+arc_pad+arc_r*2, y0+arc_pad+arc_r*2], 180, 270, fill=gold, width=thickness)
        draw.arc([x1-arc_pad-arc_r*2, y0+arc_pad, x1-arc_pad, y0+arc_pad+arc_r*2], 270, 360, fill=gold, width=thickness)
        draw.arc([x0+arc_pad, y1-arc_pad-arc_r*2, x0+arc_pad+arc_r*2, y1-arc_pad], 90, 180, fill=gold, width=thickness)
        draw.arc([x1-arc_pad-arc_r*2, y1-arc_pad-arc_r*2, x1-arc_pad, y1-arc_pad], 0, 90, fill=gold, width=thickness)

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

    def build_card_layout(self, a4_sheet, cell_img, cell_w, cell_h):
        """Original layout: 1 large portrait + 8 small photos (2x4)"""
        clothes_color = self.get_clothes_color(self.chosen_bg_rgba)
        bg_removed = self.chosen_bg_rgba
        
        large_w_px, large_h_px = self.mm_to_px(120), self.mm_to_px(180)
        large_portrait = self.generate_cheerful_background(large_w_px, large_h_px, clothes_color)
        
        margin = self.mm_to_px(15)
        
        draw_large = ImageDraw.Draw(large_portrait)
        draw_large.rectangle([margin, margin, large_w_px - margin, large_h_px - margin], fill=(255, 255, 255))
        
        inner_frame_w = large_w_px - (2 * margin)
        inner_frame_h = large_h_px - (2 * margin)
        
        ratio = inner_frame_w / float(bg_removed.width)
        new_subject_h = int(bg_removed.height * ratio)
        
        if new_subject_h > inner_frame_h:
            ratio = inner_frame_h / float(bg_removed.height)
            new_subject_h = inner_frame_h
            new_subject_w = int(bg_removed.width * ratio)
            paste_x = margin + (inner_frame_w - new_subject_w) // 2
            subject_resized = bg_removed.resize((new_subject_w, new_subject_h), Image.Resampling.LANCZOS)
        else:
            subject_resized = bg_removed.resize((inner_frame_w, new_subject_h), Image.Resampling.LANCZOS)
            paste_x = margin
            
        paste_y = large_h_px - margin - new_subject_h 
        
        large_portrait.paste(subject_resized, (paste_x, paste_y), mask=subject_resized.split()[3])
        
        self.draw_wavy_gold_border(draw_large, margin, margin, large_w_px - margin, large_h_px - margin)
        
        large_landscape = large_portrait.rotate(90, expand=True)
        
        a4_w, a4_h = self.mm_to_px(210), self.mm_to_px(297)
        margin_a4 = self.mm_to_px(15)
        total_width_area = self.mm_to_px(180)
        
        large_landscape_w = self.mm_to_px(180)
        large_landscape_h = self.mm_to_px(120)
        large_x = margin_a4 + (total_width_area - large_landscape_w) // 2
        
        a4_sheet.paste(large_landscape, (large_x, margin_a4))
        
        start_y = margin_a4 + large_landscape_h + self.mm_to_px(15)
        gap_x = (total_width_area - (4 * cell_w)) / 3 
        gap_y = self.mm_to_px(10)
        
        for row in range(2):
            for col in range(4):
                x = margin_a4 + col * (cell_w + gap_x)
                y = start_y + row * (cell_h + gap_y)
                a4_sheet.paste(cell_img, (int(x), int(y)))

    def build_grid_layout(self, a4_sheet, cell_img, cell_w, cell_h):
        """Grid layout: 16 small photos (4x4) filling the A4 sheet"""
        a4_w, a4_h = self.mm_to_px(210), self.mm_to_px(297)
        margin_a4 = self.mm_to_px(10)
        
        usable_w = a4_w - 2 * margin_a4
        usable_h = a4_h - 2 * margin_a4
        
        cols = 4
        rows = 4
        
        gap_x = (usable_w - cols * cell_w) / (cols - 1) if cols > 1 else 0
        gap_y = (usable_h - rows * cell_h) / (rows - 1) if rows > 1 else 0
        
        for row in range(rows):
            for col in range(cols):
                x = margin_a4 + col * (cell_w + gap_x)
                y = margin_a4 + row * (cell_h + gap_y)
                a4_sheet.paste(cell_img, (int(x), int(y)))

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
        
        self.root.title("Generating Final PDF...")
        self.root.update()

        # Build the cell image (40x60 + date)
        cell_img, cell_w, cell_h = self.build_cell_image(bg_removed)
        
        # Build A4 sheet
        a4_w, a4_h = self.mm_to_px(210), self.mm_to_px(297)
        a4_sheet = Image.new("RGB", (a4_w, a4_h), (255, 255, 255))
        
        # Branch based on layout mode
        if self.layout_mode == "card":
            self.build_card_layout(a4_sheet, cell_img, cell_w, cell_h)
            suffix = "_Card"
        else:
            self.build_grid_layout(a4_sheet, cell_img, cell_w, cell_h)
            suffix = "_Grid16"
        
        save_path = os.path.join(os.path.dirname(self.filepath), f"Print_Ready_Sheet{suffix}.pdf")
        a4_sheet.save(save_path, "PDF", resolution=300)
        
        messagebox.showinfo("Success", f"Processing completed successfully!\nLayout: {self.layout_mode.upper()}\nPDF saved at:\n{save_path}")
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCropper(root)
    root.mainloop()
