import tkinter as tk
from tkinter import ttk, messagebox
import os
import time
import multiprocessing
import random
import math
import subprocess
import threading
import queue

# --- Helper Math ---
def vec_sub(v1, v2): return (v1[0]-v2[0], v1[1]-v2[1], v1[2]-v2[2])
def vec_dot(v1, v2): return v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
def vec_norm(v):
    mag = math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])
    if mag == 0: return (0,0,0)
    return (v[0]/mag, v[1]/mag, v[2]/mag)
def vec_add(v1, v2): return (v1[0]+v2[0], v1[1]+v2[1], v1[2]+v2[2])
def vec_mul(v, s): return (v[0]*s, v[1]*s, v[2]*s)
def vec_cross(a, b): return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])
def vec_reflect(v, n):
    dot = vec_dot(v, n)
    return vec_sub(v, vec_mul(n, 2.0 * dot))

# --- CPU Ray Tracing Workers ---
def intersect_scene(ray_origin, ray_dir, spheres):
    t_min = 99999.0
    hit_obj = None
    for sphere in spheres:
        oc = vec_sub(ray_origin, (sphere[0], sphere[1], sphere[2]))
        a = vec_dot(ray_dir, ray_dir)
        b = 2.0 * vec_dot(oc, ray_dir)
        c = vec_dot(oc, oc) - sphere[3]*sphere[3]
        discriminant = b*b - 4*a*c
        if discriminant > 0:
            t = (-b - math.sqrt(discriminant)) / (2.0*a)
            if 0.001 < t < t_min:
                t_min = t
                hit_obj = sphere
    return t_min, hit_obj

def trace_ray(ray_origin, ray_dir, spheres, light_pos, depth):
    if depth <= 0: return (0, 0, 0)
    t, hit_obj = intersect_scene(ray_origin, ray_dir, spheres)
    if hit_obj is None: return (10, 10, 15) # Darker background

    hit_point = vec_add(ray_origin, vec_mul(ray_dir, t))
    sphere_center = (hit_obj[0], hit_obj[1], hit_obj[2])
    normal = vec_norm(vec_sub(hit_point, sphere_center))

    to_light = vec_sub(light_pos, hit_point)
    dist_to_light = math.sqrt(vec_dot(to_light, to_light))
    to_light = vec_norm(to_light)

    shadow_origin = vec_add(hit_point, vec_mul(normal, 0.001))
    shadow_t, shadow_obj = intersect_scene(shadow_origin, to_light, spheres)

    in_shadow = False
    if shadow_obj and shadow_t < dist_to_light: in_shadow = True

    diffuse = max(0.0, vec_dot(normal, to_light))
    if in_shadow: diffuse *= 0.1

    base = hit_obj[4]
    local = (base[0]*(0.2+0.8*diffuse), base[1]*(0.2+0.8*diffuse), base[2]*(0.2+0.8*diffuse))

    reflectivity = hit_obj[5]
    if reflectivity > 0:
        reflected_dir = vec_reflect(ray_dir, normal)
        ref_col = trace_ray(shadow_origin, reflected_dir, spheres, light_pos, depth - 1)
        return (local[0]*(1-reflectivity) + ref_col[0]*reflectivity,
                local[1]*(1-reflectivity) + ref_col[1]*reflectivity,
                local[2]*(1-reflectivity) + ref_col[2]*reflectivity)
    else:
        return local

def render_worker(task_queue, result_queue, stop_event):
    # Updated Colors for CPU Test as well (Neon)
    spheres = [
        (0.0, -0.2, 3.0, 0.8, (0, 255, 255), 0.5),    # Cyan
        (1.5, -0.4, 3.2, 0.6, (255, 0, 255), 0.4),    # Magenta
        (-1.5, -0.4, 3.2, 0.6, (50, 255, 50), 0.4),   # Lime
        (0.6, -0.7, 2.2, 0.3, (255, 255, 0), 0.6),    # Yellow
        (-0.6, -0.7, 2.2, 0.3, (255, 100, 0), 0.6),   # Orange
        (0.0, -5001.0, 0.0, 5000, (50, 50, 50), 0.5)  # Floor
    ]
    while not stop_event.is_set():
        try: task = task_queue.get(timeout=0.5)
        except: continue
        tx, ty, tw, th, width, height, lx = task
        light_pos = (lx, 10.0, -5.0)
        block_data = []
        aspect = width / height
        samples = 8
        for y in range(ty, ty + th):
            row = []
            for x in range(tx, tx + tw):
                ar, ag, ab = 0, 0, 0
                for _ in range(samples):
                    uv_x = (x + random.random() - 0.5) / width
                    uv_y = (y + random.random() - 0.5) / height
                    sx = (2 * uv_x - 1) * aspect
                    sy = (1 - 2 * uv_y)
                    col = trace_ray((0,0,-1), vec_norm((sx,sy,2.0)), spheres, light_pos, 5)
                    ar+=col[0]; ag+=col[1]; ab+=col[2]
                fc = (int(min(255, ar/samples)), int(min(255, ag/samples)), int(min(255, ab/samples)))
                row.append(f"#{fc[0]:02x}{fc[1]:02x}{fc[2]:02x}")
            block_data.append(row)
        result_queue.put((tx, ty, block_data))

# --- Main App ---
class TuxBench(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tux Bench")
        self.geometry("1000x800")
        self.minsize(900, 700)
        self.colors = {"bg": "#242424", "fg": "#ffffff", "header": "#303030", "card": "#383838",
                       "accent": "#3584e4", "danger": "#e01b24", "success": "#33d17a"}
        self.configure(bg=self.colors["bg"])
        self.cpu_stress_window = None
        self.cpu_model, self.cpu_cache = self.get_cpu_info()
        self.gpu_model, self.gpu_driver = self.detect_gpu_detailed()
        self.setup_styles()
        self.create_layout()
        self.update_stats()

    def setup_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure(".", background=self.colors["bg"], foreground=self.colors["fg"], font=("Cantarell", 11))
        self.style.configure("Card.TFrame", background=self.colors["card"], relief="flat")
        self.style.configure("Header.TFrame", background=self.colors["header"])
        self.style.configure("Accent.TButton", background=self.colors["accent"], foreground="white", borderwidth=0, font=("Cantarell", 11, "bold"))
        self.style.map("Accent.TButton", background=[("active", "#1c71d8"), ("pressed", "#1a5fb4")])
        self.style.configure("Danger.TButton", background=self.colors["danger"], foreground="white", borderwidth=0, font=("Cantarell", 11, "bold"))
        self.style.map("Danger.TButton", background=[("active", "#c01c28")])
        self.style.configure("Horizontal.TProgressbar", troughcolor=self.colors["card"], background=self.colors["accent"], bordercolor=self.colors["bg"], lightcolor=self.colors["accent"], darkcolor=self.colors["accent"])

    def create_layout(self):
        header = ttk.Frame(self, style="Header.TFrame", padding=(20, 10))
        header.pack(fill="x")
        tk.Label(header, text="Tux Bench", font=("Cantarell", 18, "bold"), bg=self.colors["header"], fg=self.colors["fg"]).pack(side="left")
        main = tk.Frame(self, bg=self.colors["bg"])
        main.pack(fill="both", expand=True, padx=20, pady=20)

        # Monitor
        stats = ttk.Frame(main, style="Card.TFrame", padding=20)
        stats.pack(side="left", fill="both", expand=True, padx=(0, 10))
        tk.Label(stats, text="System Monitor", font=("Cantarell", 14, "bold"), bg=self.colors["card"], fg=self.colors["fg"]).pack(anchor="w", pady=(0, 10))

        self.create_row(stats, "PROCESSOR")
        self.lbl_cpu_load = self.create_val(stats, "Usage")
        self.bar_cpu = ttk.Progressbar(stats, orient="horizontal", length=100, mode="determinate")
        self.bar_cpu.pack(fill="x", pady=(2, 10))
        self.lbl_cpu_freq = self.create_val(stats, "Clock Speed")
        self.lbl_cpu_temp = self.create_val(stats, "Temperature")

        ttk.Separator(stats, orient="horizontal").pack(fill="x", pady=15)
        self.create_row(stats, "MEMORY")
        self.lbl_mem_usage = self.create_val(stats, "Usage")
        self.bar_mem = ttk.Progressbar(stats, orient="horizontal", length=100, mode="determinate")
        self.bar_mem.pack(fill="x", pady=(2, 10))

        ttk.Separator(stats, orient="horizontal").pack(fill="x", pady=15)
        self.create_row(stats, "HARDWARE")
        tk.Label(stats, text=self.cpu_model, bg=self.colors["card"], fg=self.colors["accent"], font=("Cantarell", 10, "bold"), wraplength=350, justify="left").pack(anchor="w")
        tk.Label(stats, text=self.gpu_model, bg=self.colors["card"], fg=self.colors["accent"], font=("Cantarell", 10, "bold"), wraplength=350, justify="left").pack(anchor="w")

        self.lbl_sys_info = tk.Label(stats, text="...", justify="left", bg=self.colors["card"], fg="#5e5c64", font=("Monospace", 9))
        self.lbl_sys_info.pack(anchor="w", pady=(20, 0))

        # Controls
        ctrl = ttk.Frame(main, style="Card.TFrame", padding=20)
        ctrl.pack(side="right", fill="both", expand=True, padx=(10, 0))
        tk.Label(ctrl, text="Benchmark Suite", font=("Cantarell", 14, "bold"), bg=self.colors["card"], fg=self.colors["fg"]).pack(anchor="w", pady=(0, 20))

        self.btn_stress_cpu = ttk.Button(ctrl, text="Start CPU Stress Test", style="Accent.TButton", command=self.toggle_cpu_stress)
        self.btn_stress_cpu.pack(fill="x", pady=10)
        self.lbl_stress_status = tk.Label(ctrl, text="Status: Idle", bg=self.colors["card"], fg="#9a9996")
        self.lbl_stress_status.pack(pady=(0, 20))

        ttk.Separator(ctrl, orient="horizontal").pack(fill="x", pady=10)
        tk.Label(ctrl, text="GPU / 3D Graphics", font=("Cantarell", 11, "bold"), bg=self.colors["card"], fg=self.colors["fg"]).pack(anchor="w", pady=(5, 5))

        self.btn_reactor = ttk.Button(ctrl, text="Launch Reactor Core", style="Accent.TButton", command=self.launch_reactor)
        self.btn_reactor.pack(fill="x", pady=5)
        tk.Label(ctrl, text="Software Rasterizer & Pseudo-Ray Tracing (Compositor Stress)", bg=self.colors["card"], fg="#9a9996", font=("Cantarell", 9)).pack()

    def create_row(self, p, t): tk.Label(p, text=t, bg=self.colors["card"], fg="#5e5c64", font=("Cantarell", 9, "bold")).pack(anchor="w", pady=5)
    def create_val(self, p, t):
        f = tk.Frame(p, bg=self.colors["card"])
        f.pack(fill="x", pady=2)
        tk.Label(f, text=t, bg=self.colors["card"], fg="#deddda").pack(side="left")
        v = tk.Label(f, text="...", bg=self.colors["card"], fg=self.colors["accent"], font=("Cantarell", 11, "bold"))
        v.pack(side="right")
        return v

    def get_cpu_info(self):
        m, c = "Unknown CPU", "Unknown Cache"
        try:
            with open("/proc/cpuinfo") as f:
                for l in f:
                    if "model name" in l: m = l.split(":")[1].strip()
                    if "cache size" in l: c = l.split(":")[1].strip(); break
        except: pass
        return m, c

    def detect_gpu_detailed(self):
        g, d = "Unknown GPU", "Unknown Driver"
        try:
            o = subprocess.check_output("lspci -k | grep -A 2 -E 'VGA|3D'", shell=True).decode().split('\n')
            if o:
                g = o[0].split(':')[-1].strip()
                for l in o:
                    if "Kernel driver" in l: d = l.split(":")[1].strip(); break
        except: pass
        return g, d

    def get_temp(self):
        temps = []
        # Method 1: /sys/class/thermal
        try:
            base = "/sys/class/thermal"
            if os.path.exists(base):
                for zone in os.listdir(base):
                    if zone.startswith("thermal_zone"):
                        path = os.path.join(base, zone, "temp")
                        if os.path.exists(path):
                            try:
                                with open(path) as f:
                                    t = int(f.read().strip()) / 1000
                                    # Filter reasonable range
                                    if 0 < t < 150: temps.append(t)
                            except: pass
        except: pass

        # Method 2: /sys/class/hwmon
        try:
            base = "/sys/class/hwmon"
            if os.path.exists(base):
                for hw in os.listdir(base):
                    hw_path = os.path.join(base, hw)
                    if os.path.isdir(hw_path):
                        for f in os.listdir(hw_path):
                            if f.startswith("temp") and f.endswith("_input"):
                                try:
                                    with open(os.path.join(hw_path, f)) as f_obj:
                                        t = int(f_obj.read().strip()) / 1000
                                        if 0 < t < 150: temps.append(t)
                                except: pass
        except: pass

        if temps:
            return f"{max(temps):.1f}°C"
        return "N/A"

    def update_stats(self):
        # CPU Load
        try:
            with open("/proc/loadavg", "r") as f:
                l = float(f.read().split()[0])
                lp = min((l/multiprocessing.cpu_count())*100, 100)
                self.lbl_cpu_load.config(text=f"{int(lp)}%")
                self.bar_cpu['value'] = lp
        except: pass

        # RAM Usage (Improved)
        try:
            with open("/proc/meminfo") as f:
                mem = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(':')
                        try: val = int(parts[1]) # kB
                        except: continue
                        mem[key] = val

                total = mem.get('MemTotal', 1)
                available = mem.get('MemAvailable', 0)

                # Fallback if MemAvailable missing (older kernels)
                if available == 0:
                    free = mem.get('MemFree', 0)
                    buffers = mem.get('Buffers', 0)
                    cached = mem.get('Cached', 0)
                    available = free + buffers + cached

                used = total - available
                percent = (used / total) * 100

                # Format GB
                used_gb = used / (1024 * 1024)
                total_gb = total / (1024 * 1024)

                self.lbl_mem_usage.config(text=f"{percent:.1f}% ({used_gb:.1f}/{total_gb:.1f} GB)")
                self.bar_mem['value'] = percent
        except: pass

        # CPU Freq
        try:
            with open("/proc/cpuinfo") as f:
                for l in f:
                    if "cpu MHz" in l: self.lbl_cpu_freq.config(text=f"{float(l.split(':')[1].strip())/1000:.2f} GHz"); break
        except: pass

        self.lbl_cpu_temp.config(text=self.get_temp())

        # Uptime
        try:
            u = float(open("/proc/uptime").read().split()[0])
            self.lbl_sys_info.config(text=f"Uptime: {int(u//3600)}h {int((u%3600)//60)}m")
        except: pass

        # Check Stress Window
        if self.cpu_stress_window and not self.cpu_stress_window.winfo_exists():
            self.cpu_stress_window = None
            self.btn_stress_cpu.config(text="Start CPU Stress Test", style="Accent.TButton")
            self.lbl_stress_status.config(text="Status: Idle", fg=self.colors["success"])

        self.after(1000, self.update_stats)

    def toggle_cpu_stress(self):
        if self.cpu_stress_window:
            self.cpu_stress_window.destroy()
            self.cpu_stress_window = None
        else:
            self.cpu_stress_window = CpuRenderWindow(self)
            self.btn_stress_cpu.config(text="STOP CPU STRESS", style="Danger.TButton")
            self.lbl_stress_status.config(text="Status: RUNNING", fg=self.colors["danger"])

    def launch_reactor(self):
        ReactorCoreWindow(self)

# --- Reactor Core Engine ---
class ReactorCoreWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Reactor Core Benchmark")
        self.geometry("1024x768")
        self.configure(bg="black")

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # HUD
        self.lbl_fps = tk.Label(self, text="FPS: 0", bg="black", fg="#00ff00", font=("Monospace", 14, "bold"))
        self.lbl_fps.place(x=20, y=20)

        # Background: Starfield
        self.stars = []
        for _ in range(150):
            # 3D Star coordinates
            self.stars.append([random.uniform(-30, 30), random.uniform(-30, 30), random.uniform(-10, 30)])

        # Scene Data - Optimized & NEON COLORED
        self.meshes = []
        # Central Core (Cyan Sphere)
        self.meshes.append(self.create_sphere(1.5, 10, 10, (0, 255, 255)))
        # Inner Ring (Magenta)
        self.meshes.append(self.create_torus(2.5, 0.2, 12, 5, (255, 0, 255)))
        # Middle Ring (Lime)
        self.meshes.append(self.create_torus(3.5, 0.2, 12, 5, (50, 255, 50)))
        # Outer Ring (Yellow)
        self.meshes.append(self.create_torus(4.5, 0.2, 12, 5, (255, 255, 0)))

        # Asteroids (White/Grey)
        for _ in range(8):
            dist = 6.0 + random.random() * 4.0
            scale = 0.2 + random.random() * 0.3
            angle = random.random() * 6.28
            y = (random.random() - 0.5) * 2.0
            x = math.cos(angle) * dist
            z = math.sin(angle) * dist
            m = self.create_sphere(scale, 4, 4, (200, 200, 200))
            for v in m['verts']:
                v[0] += x; v[1] += y; v[2] += z
            self.meshes.append(m)

        self.camera_angle = 0.0
        self.running = True
        self.frame_count = 0
        self.last_time = time.time()

        self.animate()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_sphere(self, r, lat, lon, color):
        verts = []
        faces = []
        for i in range(lat + 1):
            theta = i * math.pi / lat
            for j in range(lon + 1):
                phi = j * 2 * math.pi / lon
                verts.append([r * math.sin(theta) * math.cos(phi), r * math.cos(theta), r * math.sin(theta) * math.sin(phi)])
        for i in range(lat):
            for j in range(lon):
                p1 = i * (lon + 1) + j
                faces.append([p1, p1 + 1, (i + 1) * (lon + 1) + j + 1, (i + 1) * (lon + 1) + j])
        return {'verts': verts, 'faces': faces, 'col': color, 'rot': [0,0,0], 'd_rot': [0,0,0]}

    def create_torus(self, r_main, r_tube, seg_main, seg_tube, color):
        verts = []
        faces = []
        for i in range(seg_main + 1):
            theta = i * 2 * math.pi / seg_main
            for j in range(seg_tube + 1):
                phi = j * 2 * math.pi / seg_tube
                x = (r_main + r_tube * math.cos(phi)) * math.cos(theta)
                y = (r_main + r_tube * math.cos(phi)) * math.sin(theta)
                z = r_tube * math.sin(phi)
                verts.append([x, y, z])
        for i in range(seg_main):
            for j in range(seg_tube):
                p1 = i * (seg_tube + 1) + j
                faces.append([p1, (i + 1) * (seg_tube + 1) + j, (i + 1) * (seg_tube + 1) + j + 1, p1 + 1])
        dr = [random.random()*0.05, random.random()*0.05, random.random()*0.05]
        return {'verts': verts, 'faces': faces, 'col': color, 'rot': [0,0,0], 'd_rot': dr}

    def animate(self):
        if not self.running: return
        self.canvas.delete("all")

        w = self.winfo_width()
        h = self.winfo_height()
        cx, cy = w/2, h/2

        # CAMERA: Fixed Orbit position
        cam_dist = 14.0
        cam_x = math.sin(self.camera_angle) * cam_dist
        cam_z = math.cos(self.camera_angle) * cam_dist
        cam_y = 0.0

        # Camera Rotation Precompute (LookAt 0,0,0)
        cos_c = math.cos(-self.camera_angle)
        sin_c = math.sin(-self.camera_angle)

        # --- Draw Starfield (Background) ---
        # Simple parallax based on camera angle
        # Since camera is fixed at 0 angle (in this version), let's just draw them static or rotating slightly
        # to simulate "orbiting" feeling even if geometry is centered.

        star_rot = time.time() * 0.05
        cos_s = math.cos(star_rot)
        sin_s = math.sin(star_rot)

        for star in self.stars:
            sx, sy, sz = star
            # Rotate stars
            rx = sx * cos_s - sz * sin_s
            rz = sx * sin_s + sz * cos_s
            # Project
            dist = rz + 20.0
            if dist > 0.1:
                px = cx + (rx * 400) / dist
                py = cy + (sy * 400) / dist
                size = max(1, 40 / dist)
                self.canvas.create_oval(px, py, px+size, py+size, fill="white", outline="")

        render_list = []

        for obj in self.meshes:
            # Update rotation
            obj['rot'][0] += obj['d_rot'][0]
            obj['rot'][1] += obj['d_rot'][1]
            obj['rot'][2] += obj['d_rot'][2]

            rx, ry, rz = obj['rot']
            cx_r, sx_r = math.cos(rx), math.sin(rx)
            cy_r, sy_r = math.cos(ry), math.sin(ry)
            cz_r, sz_r = math.cos(rz), math.sin(rz)

            view_verts = []

            for v in obj['verts']:
                x, y, z = v
                # Obj Rotation
                y, z = y*cx_r - z*sx_r, y*sx_r + z*cx_r
                x, z = x*cy_r - z*sy_r, x*sy_r + z*cy_r
                x, y = x*cz_r - y*sz_r, x*sz_r + y*cz_r

                # Camera Transform
                vx = x - cam_x
                vy = y - cam_y
                vz = z - cam_z
                # Rotate Y (Orbit View)
                rx_v = vx * cos_c - vz * sin_c
                rz_v = vx * sin_c + vz * cos_c

                view_verts.append([rx_v, vy, rz_v])

            for face in obj['faces']:
                p1 = view_verts[face[0]]
                p2 = view_verts[face[1]]
                p3 = view_verts[face[2]]

                # Normal
                v1 = vec_sub(p2, p1)
                v2 = vec_sub(p3, p1)
                nx = v1[1]*v2[2] - v1[2]*v2[1]
                ny = v1[2]*v2[0] - v1[0]*v2[2]
                nz = v1[0]*v2[1] - v1[1]*v2[0]

                # Backface Cull
                cx_f = (p1[0]+p3[0])*0.5
                cy_f = (p1[1]+p3[1])*0.5
                cz_f = (p1[2]+p3[2])*0.5
                if (cx_f*nx + cy_f*ny + cz_f*nz) >= 0: continue

                # Normalize
                mag = math.sqrt(nx*nx + ny*ny + nz*nz)
                if mag == 0: continue
                nx, ny, nz = nx/mag, ny/mag, nz/mag

                # --- LIGHTING & REFLECTIONS (Pseudo-Ray Trace) ---

                # 1. Diffuse (Directional Light)
                # Light coming from top-left-viewer
                lx, ly, lz = 0.5, -0.5, -0.8
                dot = nx*lx + ny*ly + nz*lz
                diffuse = 0.2 + 0.6 * max(0.0, dot)

                # 2. Specular (Phong)
                # Reflection vector R = V - 2(V.N)N ?? No, R = L - 2(L.N)N ...
                # Actually, simplified blinn-phong or just reflect view vector
                # Let's calculate Reflection of VIEW vector off NORMAL
                # View vector is roughly (0,0,1) in this space
                vx_v, vy_v, vz_v = 0, 0, 1
                dot_v = nx*vx_v + ny*vy_v + nz*vz_v
                rx_v = vx_v - 2 * dot_v * nx
                ry_v = vy_v - 2 * dot_v * ny
                rz_v = vz_v - 2 * dot_v * nz

                # Specular Hotspot
                spec = max(0.0, rx_v*lx + ry_v*ly + rz_v*lz) # Align reflection with light
                spec = spec ** 10 # Shininess

                # 3. Environment Map (Fake Reflection)
                # Map reflection vector Y component to sky/ground color
                # If pointing up (-Y), reflect Cyan. If down (+Y), reflect Purple
                env_r, env_g, env_b = 0, 0, 0
                if ry_v < 0: # Pointing Up (Screen space Y is down)
                    factor = min(1.0, abs(ry_v))
                    env_g = int(255 * factor) # Cyanish
                    env_b = int(255 * factor)
                else: # Pointing Down
                    factor = min(1.0, abs(ry_v))
                    env_r = int(100 * factor)
                    env_b = int(200 * factor)

                # Combine Colors
                # Base * Diffuse + Specular + Environment
                base = obj['col']

                fin_r = int(base[0] * diffuse * 0.6 + env_r * 0.3 + spec * 200)
                fin_g = int(base[1] * diffuse * 0.6 + env_g * 0.3 + spec * 200)
                fin_b = int(base[2] * diffuse * 0.6 + env_b * 0.3 + spec * 200)

                # Clamp
                fin_r = min(255, max(0, fin_r))
                fin_g = min(255, max(0, fin_g))
                fin_b = min(255, max(0, fin_b))

                fill_hex = f"#{fin_r:02x}{fin_g:02x}{fin_b:02x}"

                # Outline Color (Pure Neon)
                r_o, g_o, b_o = obj['col']
                outline_hex = f"#{r_o:02x}{g_o:02x}{b_o:02x}"

                # Project
                poly_points = []
                avg_z = 0
                valid = True
                f_indices = face if len(face) < 5 else face[:4]

                for idx in f_indices:
                    v = view_verts[idx]
                    avg_z += v[2]
                    if v[2] >= -0.1: valid = False; break
                    f = 700
                    x = cx + (v[0] * f) / -v[2]
                    y = cy + (v[1] * f) / -v[2]
                    poly_points.append(x); poly_points.append(y)

                if valid:
                    render_list.append((avg_z / len(f_indices), poly_points, fill_hex, outline_hex))

        render_list.sort(key=lambda x: x[0])

        for _, pts, f_col, o_col in render_list:
            # Draw with Outline for Tron look
            self.canvas.create_polygon(pts, fill=f_col, outline=o_col, width=1)

        self.frame_count += 1
        now = time.time()
        if now - self.last_time >= 1.0:
            self.lbl_fps.config(text=f"FPS: {self.frame_count / (now - self.last_time):.1f}")
            self.frame_count = 0
            self.last_time = now
        self.after(10, self.animate)

    def on_close(self):
        self.running = False
        self.destroy()

class CpuRenderWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("CPU Heavy Path Tracing (Recursive + AA)")
        self.geometry("800x600")
        self.configure(bg="#111111")
        self.canvas = tk.Canvas(self, width=800, height=600, bg="#000000", highlightthickness=0)
        self.canvas.pack()
        self.img = tk.PhotoImage(width=800, height=600)
        self.canvas.create_image(0, 0, image=self.img, anchor="nw")

        self.lbl_info = tk.Label(self, text="Pass: 1 | Time: 00:00", bg="black", fg="white", font=("Monospace", 12))
        self.lbl_info.place(x=10, y=10)

        self.start_time = time.time()
        self.stop_event = multiprocessing.Event()
        self.task_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.workers = []

        self.tile_size = 40
        self.completed_tiles = 0
        self.total_tiles = 0
        self.light_x = -3.0
        self.pass_count = 1

        self.start_render_cycle()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def start_render_cycle(self):
        self.canvas.delete("all")
        self.img = tk.PhotoImage(width=800, height=600)
        self.canvas.create_image(0, 0, image=self.img, anchor="nw")
        self.completed_tiles = 0
        tiles = []
        for y in range(0, 600, self.tile_size):
            for x in range(0, 800, self.tile_size):
                w = min(self.tile_size, 800 - x)
                h = min(self.tile_size, 600 - y)
                tiles.append((x, y, w, h, 800, 600, self.light_x))
        self.total_tiles = len(tiles)
        random.shuffle(tiles)
        for t in tiles: self.task_queue.put(t)

        if not self.workers:
            for _ in range(multiprocessing.cpu_count()):
                p = multiprocessing.Process(target=render_worker, args=(self.task_queue, self.result_queue, self.stop_event))
                p.daemon = True; p.start(); self.workers.append(p)
        self.after(100, self.poll_results)

    def poll_results(self):
        if self.stop_event.is_set(): return
        elapsed = int(time.time() - self.start_time)
        self.lbl_info.config(text=f"Pass: {self.pass_count} | Time: {elapsed//60:02d}:{elapsed%60:02d}")

        for _ in range(20):
            try:
                rx, ry, data = self.result_queue.get_nowait()
                self.img.put(data, to=(rx, ry))
                self.completed_tiles += 1
            except: break

        if self.completed_tiles >= self.total_tiles:
            self.light_x += 2.0
            if self.light_x > 3.0: self.light_x = -3.0
            self.pass_count += 1
            self.after(500, self.start_render_cycle)
        else:
            self.after(10, self.poll_results)

    def on_close(self):
        self.stop_event.set()
        try:
            while True: self.task_queue.get_nowait()
        except: pass
        for p in self.workers: p.terminate()
        self.destroy()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = TuxBench()
    app.mainloop()
