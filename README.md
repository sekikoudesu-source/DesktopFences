# DesktopFences 🚀

An ultra-lightweight, intelligent, and visually stunning virtual desktop organizer built with Python and PyQt6. Say goodbye to cluttered desktops and enjoy a 100% clean, distraction-free workspace while keeping all your files perfectly categorized and instantly accessible.

---

## 🌟 V12 Core Update: Pure Virtual View Mode (Strategy 3)

DesktopFences has been completely re-architected to support **Pure Virtual View Mode (Strategy 3)**—the same industrial standard used by professional tools like Fences 3.

*   **Zero Physical File Movement**: All files and folders permanently reside on your physical desktop (`C:\Users\<username>\Desktop`). No files are moved to project subfolders, eliminating data loss risks and cross-drive copy delays.
*   **0-Second Drag & Drop**: Dragging files between virtual fences only updates the metadata configuration. Operations take less than **10ms**, regardless of the file size (no physical copying of Gigabytes of files).
*   **Auto-Hiding Native Desktop Icons**: The tray menu now features an option to **"🕶️ 隐藏原生桌面图标" (Hide Native Desktop Icons)**. The app calls Windows Win32 APIs to hide native icons programmatically.
*   **Polite Recovery on Exit**: When the application exits, it automatically makes the native Windows desktop icons visible again, ensuring your desktop returns to normal.
*   **Central Watcher & Sync**: A single global directory watcher keeps the fences synchronized with any changes on the desktop (creation, renaming, deletions) with custom debouncing.
*   **Smart "Unclassified" Bin**: Any new files created or downloaded to the desktop are automatically detected and placed in the default "未分类 (Unclassified)" fence so you never lose visibility.

---

## ✨ Features

*   **🧠 AI-Powered Smart Categorization**: 
    One-click auto-organization! Files, games, documents, and shortcuts are instantly analyzed and categorized into pre-defined smart fences (e.g., 🎮 Gaming, 💻 Dev Tools, 💼 Work & Docs, 🛠️ Utilities).
*   **👻 Edge Snapping & Auto-Hide**: 
    Drag a fence to the edge of the screen, and it will elegantly collapse into a tiny translucent sliver. Hover over it with your mouse, and it smoothly slides out.
*   **💎 Glassmorphism UI**: 
    Beautifully translucent, borderless windows with drag-and-drop support, smooth animations, and traditional vertical text rendering when snapped to the edges.
*   **📦 Standalone Executable**: 
    Compiled via PyInstaller into a single, portable `.exe` file. No Python environment needed!

---

## 🛠️ Tech Stack

*   **Python 3.12**
*   **PyQt6** (GUI, Animations, File System Watcher)
*   **Pywin32** (Windows Native API Integrations)
*   **PyInstaller** (Packaging)

---

## 🚀 Getting Started

### Using the Pre-built Executable
1. Download the latest `DesktopFences.exe` from the `dist/` directory.
2. Double-click to run. An icon will appear in your system tray.
3. Right-click the tray icon and select **"🕶️ 隐藏原生桌面图标" (Hide Native Desktop Icons)**.
4. Select **"✨ 一键智能整理桌面" (Auto-Organize Desktop)** to let the AI instantly classify your desktop clutter into beautiful fences!

### Building from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/sekikoudesu-source/DesktopFences.git
   cd DesktopFences
   ```
2. Create and activate a virtual environment, then install requirements:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```
4. Build the standalone executable:
   ```bash
   pyinstaller -F -w main.py --name DesktopFences --clean --icon=app_icon.ico --add-data "app_icon.ico;."
   ```

---

## 📜 License

This project is open-source and available under the MIT License.
