from typing import List, Tuple, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal
from utils.win32 import robust_move

class MoveWorker(QThread):
    """
    Background worker thread for performing blocking file move operations.
    Prevents the main PyQt GUI thread from freezing during massive file transfers.
    """
    
    # Emits (current_index, total_files)
    progress = pyqtSignal(int, int)
    # Emits (success_map: Dict[dst, src], failed_list: List[src])
    finished_move = pyqtSignal(dict, list)

    def __init__(self, move_tasks: List[Tuple[str, str]], parent: Any = None) -> None:
        """
        Args:
            move_tasks: List of (source_path, destination_path) tuples to process.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.move_tasks = move_tasks

    def run(self) -> None:
        """Executes the file moving logic in a background thread."""
        success_map: Dict[str, str] = {}
        failed_list: List[str] = []
        total = len(self.move_tasks)
        
        for i, (src, dst) in enumerate(self.move_tasks):
            try:
                robust_move(src, dst)
                success_map[dst] = src
            except Exception as e:
                # Catch any OS errors, PermissionErrors, or shutil errors
                failed_list.append(src)
            
            # Emit progress update
            self.progress.emit(i + 1, total)
            
        self.finished_move.emit(success_map, failed_list)
