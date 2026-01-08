"""
Indexed Files Tracker
Track which files in data_store have been processed to avoid re-indexing
"""
import os
import json
from datetime import datetime
from config import INDEXED_FILES_TRACKER


class IndexedFilesTracker:
    """Track which files in data_store have been indexed"""
    
    def __init__(self, tracker_file=INDEXED_FILES_TRACKER):
        self.tracker_file = tracker_file
        self.indexed_files = self._load()
    
    def _load(self):
        """Load tracker from disk"""
        if os.path.exists(self.tracker_file):
            with open(self.tracker_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save(self):
        """Save tracker to disk"""
        with open(self.tracker_file, 'w') as f:
            json.dump(self.indexed_files, f, indent=2)
    
    def is_indexed(self, filepath):
        """
        Check if file has been indexed.
        Also checks modification time to detect updated files.
        """
        if filepath not in self.indexed_files:
            return False
        
        # Check if file was modified since last indexing
        try:
            current_mtime = os.path.getmtime(filepath)
            stored_mtime = self.indexed_files[filepath].get('mtime', 0)
            return current_mtime <= stored_mtime
        except OSError:
            return False
    
    def mark_indexed(self, filepath, stats=None):
        """Mark file as indexed with optional stats"""
        try:
            self.indexed_files[filepath] = {
                'mtime': os.path.getmtime(filepath),
                'indexed_at': datetime.now().isoformat(),
                'stats': stats or {}
            }
            self.save()
        except OSError as e:
            print(f"Error marking file as indexed: {e}")
    
    def get_all_indexed(self):
        """Get list of all indexed file paths"""
        return list(self.indexed_files.keys())
    
    def get_file_stats(self, filepath):
        """Get stats for a specific file"""
        return self.indexed_files.get(filepath, {})
    
    def clear(self):
        """Clear all tracked files (for re-indexing)"""
        self.indexed_files = {}
        self.save()
    
    def remove(self, filepath):
        """Remove a file from tracking"""
        if filepath in self.indexed_files:
            del self.indexed_files[filepath]
            self.save()


# Create instance in graphrag_app.py to avoid circular imports
def create_tracker():
    return IndexedFilesTracker()
