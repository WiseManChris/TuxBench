# **Tux Bench 🐧**

**Tux Bench** is a lightweight, Python-based system stress testing and benchmarking tool designed specifically for Linux environments (Manjaro/Arch, Debian, etc.). It stresses your system using pure mathematical computations and software-based rendering to test CPU stability and Window Manager/Compositor performance.

## **Features**

### **🖥️ Hardware Monitor**

* **Real-time CPU Load:** Tracks usage across all cores.  
* **CPU Thermals:** Scans /sys/class/thermal and /sys/class/hwmon for the hottest sensor.  
* **Clock Speed:** Real-time frequency monitoring from /proc/cpuinfo.  
* **RAM Usage:** Accurate memory calculations parsing /proc/meminfo.  
* **Hardware Detection:** Identifies exact CPU model and GPU driver/chipset.

### **🔥 CPU Stress Test (Ray Tracing)**

* **Engine:** Recursive Path Tracer with Anti-Aliasing (8x Samples).  
* **Workload:** Spawns a dedicated process for every CPU core.  
* **Physics:** Calculates light bounces, shadows, and reflections in pure Python float math to maximize thermal load.

### **⚛️ GPU/Compositor Stress (Reactor Core)**

* **Engine:** "Reactor Core" Software Rasterizer.  
* **Workload:**  
  * Real-time 3D matrix transformations for thousands of vertices.  
  * Z-sorting (Painter's Algorithm) of thousands of polygons per frame.  
  * Pseudo-Ray-Traced lighting and environment mapping (Neon/Metallic shaders).  
* **Goal:** Stresses the Single-Threaded performance of the CPU and the 2D Rasterization/Compositing capabilities of your Linux Window Manager (X11/Wayland).

## **Installation & Requirements**

### **⚠️ Prerequisite: Python 3**

To keep the AppImage extremely small (\~1MB), Tux Bench relies on your system's **Python 3** installation.

**99% of Linux distributions come with Python pre-installed.** However, if the app does not open, you may be missing the python3-tk (Tkinter) GUI module.

Here is how to ensure you have everything needed:

**Ubuntu / Debian / Mint / Pop\!\_OS:**

sudo apt update && sudo apt install python3 python3-tk

**Arch Linux / Manjaro:**

sudo pacman \-S python tk

**Fedora / RHEL:**

sudo dnf install python3 python3-tkinter

### **Running the App via AppImage (Recommended)**

1. Download the latest .AppImage from the **Releases** page.  
2. Right-click the file \-\> **Properties** \-\> **Permissions**.  
3. Check **"Allow executing file as program"**.  
4. Double-click to run\!

*(Alternatively, run chmod \+x TuxBench-x86\_64.AppImage && ./TuxBench-x86\_64.AppImage in terminal)*

### **Running via Source Code**

If you prefer to run the raw script:

python tux\_bench.py

## **How It Works**

Tux Bench avoids heavy external dependencies like PyGame or OpenGL bindings to ensure it runs on almost any fresh Linux install. It forces the system to perform heavy graphical tasks using software rendering, which effectively exposes instability in CPU overclocks or Window Manager configurations.

