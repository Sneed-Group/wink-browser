"""
Download manager for the browser.
"""

import logging
import os
import time
import threading
import queue
import uuid
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

class DownloadStatus(Enum):
    """Download status enum."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class DownloadItem:
    """Download item class."""
    
    def __init__(self, url: str, file_path: str, 
                 file_name: Optional[str] = None,
                 headers: Optional[Dict[str, str]] = None):
        """
        Initialize download item.
        
        Args:
            url: URL to download
            file_path: Path to save the file
            file_name: File name (defaults to URL basename)
            headers: Additional headers
        """
        self.id = str(uuid.uuid4())
        self.url = url
        self.file_path = file_path
        
        # Set file name
        if file_name:
            self.file_name = file_name
        else:
            # Extract file name from URL
            self.file_name = os.path.basename(url.split('?')[0])
            if not self.file_name:
                self.file_name = f"download_{int(time.time())}"
        
        # Full path to save the file
        self.full_path = os.path.join(file_path, self.file_name)
        
        self.headers = headers or {}
        self.status = DownloadStatus.PENDING
        self.progress = 0.0  # 0.0 to 1.0
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.start_time = 0.0
        self.end_time = 0.0
        self.error = None
        self.speed = 0.0  # Bytes per second
        self.paused = False
        self.canceled = False
        
        # For resumable downloads
        self.resumable = False
        self.range_start = 0
        
        # For callbacks
        self.progress_callbacks = []
        
        logger.debug(f"Download item created: {self.url} -> {self.full_path}")
    
    def update_progress(self, downloaded_bytes: int, total_bytes: int) -> None:
        """
        Update progress.
        
        Args:
            downloaded_bytes: Bytes downloaded
            total_bytes: Total bytes to download
        """
        self.downloaded_bytes = downloaded_bytes
        
        if total_bytes > 0:
            self.total_bytes = total_bytes
            self.progress = downloaded_bytes / total_bytes
        
        # Calculate speed
        if self.start_time > 0:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                self.speed = downloaded_bytes / elapsed
        
        # Call progress callbacks
        for callback in self.progress_callbacks:
            try:
                callback(self)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def add_progress_callback(self, callback: Callable[['DownloadItem'], None]) -> None:
        """
        Add progress callback.
        
        Args:
            callback: Callback function
        """
        self.progress_callbacks.append(callback)
    
    def set_status(self, status: DownloadStatus, error: Optional[str] = None) -> None:
        """
        Set download status.
        
        Args:
            status: New status
            error: Error message
        """
        self.status = status
        
        if status == DownloadStatus.DOWNLOADING:
            if self.start_time == 0:
                self.start_time = time.time()
        elif status in (DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELED):
            self.end_time = time.time()
        
        if error:
            self.error = error
        
        logger.debug(f"Download {self.id} status: {status.value}")
    
    def get_elapsed_time(self) -> float:
        """
        Get elapsed download time.
        
        Returns:
            float: Elapsed time in seconds
        """
        if self.start_time == 0:
            return 0
        
        if self.end_time > 0:
            return self.end_time - self.start_time
        
        return time.time() - self.start_time
    
    def get_estimated_time(self) -> float:
        """
        Get estimated time remaining.
        
        Returns:
            float: Estimated time in seconds
        """
        if self.speed == 0 or self.total_bytes == 0:
            return 0
        
        remaining_bytes = self.total_bytes - self.downloaded_bytes
        return remaining_bytes / self.speed
    
    def get_formatted_speed(self) -> str:
        """
        Get formatted speed.
        
        Returns:
            str: Formatted speed
        """
        if self.speed == 0:
            return "0 B/s"
        
        # Format speed
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        size = self.speed
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"
    
    def get_formatted_size(self, size: Optional[int] = None) -> str:
        """
        Get formatted size.
        
        Args:
            size: Size to format (defaults to total_bytes)
            
        Returns:
            str: Formatted size
        """
        if size is None:
            size = self.total_bytes
        
        if size == 0:
            return "0 B"
        
        # Format size
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size_val = size
        unit_index = 0
        
        while size_val >= 1024 and unit_index < len(units) - 1:
            size_val /= 1024
            unit_index += 1
        
        return f"{size_val:.2f} {units[unit_index]}"
    
    def is_complete(self) -> bool:
        """
        Check if download is complete.
        
        Returns:
            bool: True if download is complete
        """
        return self.status == DownloadStatus.COMPLETED
    
    def is_paused(self) -> bool:
        """
        Check if download is paused.
        
        Returns:
            bool: True if download is paused
        """
        return self.status == DownloadStatus.PAUSED
    
    def is_failed(self) -> bool:
        """
        Check if download failed.
        
        Returns:
            bool: True if download failed
        """
        return self.status == DownloadStatus.FAILED
    
    def is_canceled(self) -> bool:
        """
        Check if download is canceled.
        
        Returns:
            bool: True if download is canceled
        """
        return self.status == DownloadStatus.CANCELED


class DownloadManager:
    """Download manager for the browser."""
    
    def __init__(self, default_download_path: Optional[str] = None,
                 max_concurrent_downloads: int = 3,
                 network_manager = None):
        """
        Initialize download manager.
        
        Args:
            default_download_path: Default download path
            max_concurrent_downloads: Maximum number of concurrent downloads
            network_manager: Network manager to use
        """
        # Set default download path
        if not default_download_path:
            self.default_download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        else:
            self.default_download_path = default_download_path
        
        # Create directory if it doesn't exist
        os.makedirs(self.default_download_path, exist_ok=True)
        
        self.max_concurrent_downloads = max_concurrent_downloads
        self.network_manager = network_manager
        
        # Downloads
        self.downloads: Dict[str, DownloadItem] = {}
        self.download_queue = queue.Queue()
        self.active_downloads = 0
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        # Start download worker thread
        self._running = True
        self._worker_thread = threading.Thread(target=self._download_worker, daemon=True)
        self._worker_thread.start()
        
        logger.debug(f"Download manager initialized (default_path: {self.default_download_path})")
    
    def _download_worker(self) -> None:
        """Download worker thread."""
        while self._running:
            try:
                # Get item from queue
                download_id = self.download_queue.get(timeout=1)
                
                # Skip if not found (might have been canceled)
                if download_id not in self.downloads:
                    self.download_queue.task_done()
                    continue
                
                # Get download item
                download = self.downloads[download_id]
                
                # Skip if paused or canceled
                if download.paused or download.canceled:
                    self.download_queue.task_done()
                    continue
                
                # Increment active downloads counter
                with self._lock:
                    self.active_downloads += 1
                
                # Set status to downloading
                download.set_status(DownloadStatus.DOWNLOADING)
                
                # Start download
                self._start_download(download)
                
                # Decrement active downloads counter
                with self._lock:
                    self.active_downloads -= 1
                
                # Mark task as done
                self.download_queue.task_done()
                
                # Check queue for next download
                self._check_queue()
                
            except queue.Empty:
                # Queue is empty, wait for new downloads
                pass
            except Exception as e:
                logger.error(f"Error in download worker: {e}")
    
    def _start_download(self, download: DownloadItem) -> None:
        """
        Start download.
        
        Args:
            download: Download item
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(download.file_path, exist_ok=True)
            
            # Handle resumable downloads
            if download.resumable and download.range_start > 0:
                download.headers['Range'] = f'bytes={download.range_start}-'
            
            # Progress callback for network manager
            def progress_callback(progress, downloaded, total, elapsed):
                download.update_progress(downloaded, total)
            
            # Check if network manager is available
            if self.network_manager:
                # Download using network manager
                result = self.network_manager.download_file(
                    download.url,
                    download.full_path,
                    headers=download.headers,
                    progress_callback=progress_callback
                )
                
                if result:
                    download.set_status(DownloadStatus.COMPLETED)
                else:
                    download.set_status(DownloadStatus.FAILED, "Download failed")
            else:
                # Fallback to urllib
                try:
                    import requests
                    
                    # Make a streaming request
                    with requests.get(
                        download.url,
                        headers=download.headers,
                        stream=True,
                        timeout=30
                    ) as response:
                        response.raise_for_status()
                        
                        # Get total file size
                        total_size = int(response.headers.get('content-length', 0))
                        download.total_bytes = total_size
                        
                        # Check for resumable downloads
                        if 'accept-ranges' in response.headers:
                            download.resumable = True
                        
                        # Download the file
                        with open(download.full_path, 'wb') as f:
                            downloaded = 0
                            start_time = time.time()
                            
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk and not download.canceled and not download.paused:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    download.update_progress(downloaded, total_size)
                                
                                # Check if download was paused or canceled
                                if download.paused:
                                    download.set_status(DownloadStatus.PAUSED)
                                    download.range_start = downloaded
                                    return
                                elif download.canceled:
                                    download.set_status(DownloadStatus.CANCELED)
                                    # Remove partial file
                                    if os.path.exists(download.full_path):
                                        os.unlink(download.full_path)
                                    return
                        
                        download.set_status(DownloadStatus.COMPLETED)
                
                except Exception as e:
                    logger.error(f"Error downloading file: {e}")
                    download.set_status(DownloadStatus.FAILED, str(e))
                    
                    # Remove partial file
                    if os.path.exists(download.full_path):
                        os.unlink(download.full_path)
        
        except Exception as e:
            logger.error(f"Error starting download: {e}")
            download.set_status(DownloadStatus.FAILED, str(e))
    
    def _check_queue(self) -> None:
        """Check if we can start more downloads."""
        with self._lock:
            # If we have room for more downloads, start them from the queue
            if self.active_downloads < self.max_concurrent_downloads:
                # Check for paused/queued downloads
                for download_id, download in self.downloads.items():
                    if download.status == DownloadStatus.PENDING and not download.paused:
                        self.download_queue.put(download_id)
                        break
    
    def download(self, url: str, file_path: Optional[str] = None, 
                 file_name: Optional[str] = None,
                 headers: Optional[Dict[str, str]] = None) -> DownloadItem:
        """
        Add a download.
        
        Args:
            url: URL to download
            file_path: Path to save the file (defaults to default_download_path)
            file_name: File name (defaults to URL basename)
            headers: Additional headers
            
        Returns:
            DownloadItem: Download item
        """
        if not file_path:
            file_path = self.default_download_path
        
        # Create download item
        download = DownloadItem(url, file_path, file_name, headers)
        
        # Add to downloads
        with self._lock:
            self.downloads[download.id] = download
        
            # Add to queue if we have room for more downloads
            if self.active_downloads < self.max_concurrent_downloads:
                self.download_queue.put(download.id)
            
        logger.debug(f"Added download: {url}")
        return download
    
    def pause(self, download_id: str) -> bool:
        """
        Pause a download.
        
        Args:
            download_id: Download ID
            
        Returns:
            bool: True if download was paused
        """
        if download_id not in self.downloads:
            logger.warning(f"Download not found: {download_id}")
            return False
        
        download = self.downloads[download_id]
        
        if download.status != DownloadStatus.DOWNLOADING:
            logger.warning(f"Cannot pause download {download_id}: not downloading")
            return False
        
        download.paused = True
        
        logger.debug(f"Paused download: {download_id}")
        return True
    
    def resume(self, download_id: str) -> bool:
        """
        Resume a download.
        
        Args:
            download_id: Download ID
            
        Returns:
            bool: True if download was resumed
        """
        if download_id not in self.downloads:
            logger.warning(f"Download not found: {download_id}")
            return False
        
        download = self.downloads[download_id]
        
        if download.status != DownloadStatus.PAUSED:
            logger.warning(f"Cannot resume download {download_id}: not paused")
            return False
        
        download.paused = False
        
        # Add to queue if we have room for more downloads
        with self._lock:
            if self.active_downloads < self.max_concurrent_downloads:
                self.download_queue.put(download.id)
        
        logger.debug(f"Resumed download: {download_id}")
        return True
    
    def cancel(self, download_id: str) -> bool:
        """
        Cancel a download.
        
        Args:
            download_id: Download ID
            
        Returns:
            bool: True if download was canceled
        """
        if download_id not in self.downloads:
            logger.warning(f"Download not found: {download_id}")
            return False
        
        download = self.downloads[download_id]
        
        if download.status in (DownloadStatus.COMPLETED, DownloadStatus.CANCELED):
            logger.warning(f"Cannot cancel download {download_id}: already completed/canceled")
            return False
        
        download.canceled = True
        
        # If download is not active, set status to canceled
        if download.status != DownloadStatus.DOWNLOADING:
            download.set_status(DownloadStatus.CANCELED)
            
            # Remove partial file
            if os.path.exists(download.full_path):
                os.unlink(download.full_path)
        
        logger.debug(f"Canceled download: {download_id}")
        return True
    
    def remove(self, download_id: str) -> bool:
        """
        Remove a download from the list.
        
        Args:
            download_id: Download ID
            
        Returns:
            bool: True if download was removed
        """
        if download_id not in self.downloads:
            logger.warning(f"Download not found: {download_id}")
            return False
        
        download = self.downloads[download_id]
        
        # Cancel if not completed
        if download.status not in (DownloadStatus.COMPLETED, DownloadStatus.CANCELED, DownloadStatus.FAILED):
            self.cancel(download_id)
        
        # Remove from downloads
        with self._lock:
            del self.downloads[download_id]
        
        logger.debug(f"Removed download: {download_id}")
        return True
    
    def get_download(self, download_id: str) -> Optional[DownloadItem]:
        """
        Get a download.
        
        Args:
            download_id: Download ID
            
        Returns:
            Optional[DownloadItem]: Download item
        """
        return self.downloads.get(download_id)
    
    def get_downloads(self, status: Optional[DownloadStatus] = None) -> List[DownloadItem]:
        """
        Get all downloads.
        
        Args:
            status: Filter by status
            
        Returns:
            List[DownloadItem]: List of download items
        """
        with self._lock:
            if status:
                return [d for d in self.downloads.values() if d.status == status]
            else:
                return list(self.downloads.values())
    
    def get_active_downloads(self) -> List[DownloadItem]:
        """
        Get active downloads.
        
        Returns:
            List[DownloadItem]: List of active download items
        """
        return self.get_downloads(DownloadStatus.DOWNLOADING)
    
    def get_completed_downloads(self) -> List[DownloadItem]:
        """
        Get completed downloads.
        
        Returns:
            List[DownloadItem]: List of completed download items
        """
        return self.get_downloads(DownloadStatus.COMPLETED)
    
    def get_pending_downloads(self) -> List[DownloadItem]:
        """
        Get pending downloads.
        
        Returns:
            List[DownloadItem]: List of pending download items
        """
        return self.get_downloads(DownloadStatus.PENDING)
    
    def get_failed_downloads(self) -> List[DownloadItem]:
        """
        Get failed downloads.
        
        Returns:
            List[DownloadItem]: List of failed download items
        """
        return self.get_downloads(DownloadStatus.FAILED)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get download statistics.
        
        Returns:
            Dict[str, Any]: Download statistics
        """
        with self._lock:
            total_count = len(self.downloads)
            active_count = len(self.get_active_downloads())
            completed_count = len(self.get_completed_downloads())
            pending_count = len(self.get_pending_downloads())
            failed_count = len(self.get_failed_downloads())
            
            total_downloaded = sum(d.downloaded_bytes for d in self.downloads.values())
            total_size = sum(d.total_bytes for d in self.downloads.values() if d.total_bytes > 0)
            
            # Calculate average speed
            active_downloads = self.get_active_downloads()
            avg_speed = sum(d.speed for d in active_downloads) / len(active_downloads) if active_downloads else 0
        
        return {
            'total_count': total_count,
            'active_count': active_count,
            'completed_count': completed_count,
            'pending_count': pending_count,
            'failed_count': failed_count,
            'total_downloaded': total_downloaded,
            'total_size': total_size,
            'avg_speed': avg_speed
        }
    
    def set_default_download_path(self, path: str) -> None:
        """
        Set default download path.
        
        Args:
            path: New default download path
        """
        self.default_download_path = path
        
        # Create directory if it doesn't exist
        os.makedirs(self.default_download_path, exist_ok=True)
        
        logger.debug(f"Default download path set to: {path}")
    
    def set_max_concurrent_downloads(self, max_downloads: int) -> None:
        """
        Set maximum number of concurrent downloads.
        
        Args:
            max_downloads: Maximum number of concurrent downloads
        """
        self.max_concurrent_downloads = max_downloads
        logger.debug(f"Max concurrent downloads set to: {max_downloads}")
        
        # Check queue for new downloads
        self._check_queue()
    
    def clear_completed(self) -> int:
        """
        Clear completed downloads.
        
        Returns:
            int: Number of downloads cleared
        """
        to_remove = []
        
        with self._lock:
            for download_id, download in self.downloads.items():
                if download.status == DownloadStatus.COMPLETED:
                    to_remove.append(download_id)
            
            for download_id in to_remove:
                del self.downloads[download_id]
        
        logger.debug(f"Cleared {len(to_remove)} completed downloads")
        return len(to_remove)
    
    def close(self) -> None:
        """Close the download manager."""
        logger.debug("Closing download manager")
        self._running = False
        
        # Cancel all active downloads
        with self._lock:
            for download in self.downloads.values():
                if download.status == DownloadStatus.DOWNLOADING:
                    download.canceled = True 