# **Changelog**

All notable changes to the **Tux Bench** project will be documented in this file.

$$1.0$$  
\- 2025-11-29

### **Added**

* **ARM64 Support:** Added native support for Raspberry Pi 4/5, Orange Pi 5, and other aarch64 devices.  
* **Reactor Core Engine:** New GPU stress test featuring a spinning reactor, dynamic lighting, and pseudo-ray-traced reflections.  
* **AppImage Builds:** Automated build scripts for both x86\_64 and ARM64 architectures.  
* Improved CPU temperature detection logic (scans /sys/class/hwmon and /sys/class/thermal).  
* Updated UI with a specialized "Tux Speedometer" icon.  
* Optimized 3D math for better performance on Python.

### **Initial Release**

* **CPU Stress Test:** Recursive Path Tracer (8x Anti-Aliasing).  
* **Hardware Monitor:** Real-time tracking of CPU Load, Clock Speed, and RAM usage.  
* **Basic UI:** Dark-themed Tkinter interface.