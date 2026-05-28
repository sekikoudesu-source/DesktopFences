# DesktopFences 🚀

An ultra-lightweight, intelligent, and visually stunning virtual desktop organizer built with Python and PyQt6. Say goodbye to cluttered desktops and enjoy a 100% clean, distraction-free workspace while keeping all your files perfectly categorized and instantly accessible.

## ✨ Features

- **🧠 AI-Powered Smart Categorization**: 
  One-click auto-organization! Files, games, documents, and shortcuts are instantly analyzed and moved into pre-defined smart fences (e.g., 🎮 Gaming, 💻 Dev Tools, 💼 Work & Docs, 🛠️ Utilities).
- **🗃️ Virtual Containers**: 
  Unlike traditional fence apps that just draw boxes on your desktop, DesktopFences uses *virtual mapping*. Your desktop remains absolutely empty, while files are safely managed in virtual containers.
- **💾 Persistent Memory**: 
  Fences remember your files. Even if you manually scatter files back to the desktop, the app will magically suck them back into their correct fences upon the next startup.
- **👻 Edge Snapping & Auto-Hide**: 
  Drag a fence to the edge of the screen, and it will elegantly collapse into a tiny translucent sliver. Hover over it with your mouse, and it smoothly slides out.
- **💎 Glassmorphism UI**: 
  Beautifully translucent, borderless windows with drag-and-drop support, smooth animations, and traditional vertical text rendering when snapped to the edges.
- **📦 Standalone Executable**: 
  Compiled via PyInstaller into a single, portable `.exe` file. No Python environment needed!

## 🛠️ Tech Stack

- **Python 3.12**
- **PyQt6** (GUI, Animations, File System Watcher)
- **PyInstaller** (Packaging)

## 🚀 Getting Started

### Using the Pre-built Executable
1. Download the latest `DesktopFences.exe` from the `dist/` directory (or releases).
2. Double-click to run. An icon will appear in your system tray.
3. Right-click the tray icon and select **"✨ 一键智能整理桌面" (Auto-Organize Desktop)** to let the AI instantly classify your desktop clutter into beautiful fences!

### Building from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/DesktopFences.git
   cd DesktopFences
   ```
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```
4. Build the standalone executable:
   ```bash
   pyinstaller -F -w main.py --name DesktopFences --clean
   ```

## 🎮 Usage Tips

- **Drag & Drop**: Simply drag files from anywhere directly into a fence.
- **Resize & Move**: Hover over the edges of a fence to resize it, or drag the empty space inside a fence to move it.
- **Hide the Recycle Bin**: Since the app creates a shortcut for your Recycle Bin in the "Utilities" fence, you can safely hide the native Windows Recycle Bin icon in your Personalization settings for a 100% clean wallpaper!

## 📜 License

This project is open-source and available under the MIT License.
