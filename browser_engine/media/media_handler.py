"""
Media handler for the browser engine.
This module is responsible for handling media elements like images, audio, and video.
"""

import logging
import os
import tempfile
import threading
import time
from typing import Dict, List, Optional, Any, Tuple
import urllib.request
import urllib.parse
from pathlib import Path
import hashlib
import subprocess
import shutil
import io

# For image processing
try:
    from PIL import Image, ImageTk
except ImportError:
    logging.warning("PIL not available. Image processing will be limited.")

# For video processing with ffmpeg
FFMPEG_PATH = shutil.which('ffmpeg')
if not FFMPEG_PATH:
    logging.warning("ffmpeg not found in PATH. Video processing will be limited.")

logger = logging.getLogger(__name__)

class MediaHandler:
    """Handler for media elements (images, audio, video)."""
    
    def __init__(self, enabled: bool = True, cache_dir: Optional[str] = None):
        """
        Initialize the media handler.
        
        Args:
            enabled: Whether media handling is enabled
            cache_dir: Directory to use for caching media files
        """
        self.enabled = enabled
        
        # Create cache directory if not provided
        if not cache_dir:
            cache_dir = os.path.join(tempfile.gettempdir(), 'wink_browser', 'media_cache')
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_dir = cache_dir
        
        # Dictionary to store loaded media
        self.loaded_media = {}
        
        # Track ongoing downloads
        self.ongoing_downloads = {}
        self._lock = threading.Lock()
        
        logger.debug(f"Media handler initialized (enabled: {enabled}, cache_dir: {cache_dir})")
    
    def load_image(self, url: str, callback: Any = None) -> Optional[Tuple[str, Any]]:
        """
        Load an image from a URL.
        
        Args:
            url: URL or path to the image
            callback: Optional callback function to call when image is loaded
            
        Returns:
            Optional[Tuple[str, Any]]: Tuple of (cache_path, image_data) or None if loading failed
        """
        if not self.enabled:
            logger.warning("Media handler is disabled")
            return None
        
        # Check if image is already loaded
        if url in self.loaded_media:
            if callback:
                callback(url, self.loaded_media[url])
            return (url, self.loaded_media[url])
        
        # Start a background thread to load the image
        thread = threading.Thread(
            target=self._load_image_thread,
            args=(url, callback),
            daemon=True
        )
        thread.start()
        
        return None
    
    def _load_image_thread(self, url: str, callback: Any) -> None:
        """
        Background thread for loading an image.
        
        Args:
            url: URL or path to the image
            callback: Optional callback function to call when image is loaded
        """
        try:
            # Check if this is a local file path or a URL
            if url.startswith(('http://', 'https://')):
                # Download the image
                cache_path = self._download_file(url)
                if not cache_path:
                    logger.error(f"Failed to download image: {url}")
                    return
            else:
                # Local file path
                if os.path.exists(url):
                    cache_path = url
                else:
                    logger.error(f"Image file not found: {url}")
                    return
            
            # Load the image using PIL
            try:
                with Image.open(cache_path) as img:
                    # Convert to a format that can be used by the UI
                    image_data = img.copy()
                    
                    # Store in loaded media dictionary
                    with self._lock:
                        self.loaded_media[url] = image_data
                    
                    # Call the callback if provided
                    if callback:
                        callback(url, image_data)
            except Exception as e:
                logger.error(f"Error loading image {url}: {e}")
        except Exception as e:
            logger.error(f"Error in image loading thread for {url}: {e}")
    
    def load_video(self, url: str, callback: Any = None) -> Optional[str]:
        """
        Load a video from a URL.
        
        Args:
            url: URL or path to the video
            callback: Optional callback function to call when video is loaded
            
        Returns:
            Optional[str]: Path to the video file or None if loading failed
        """
        if not self.enabled:
            logger.warning("Media handler is disabled")
            return None
        
        if not FFMPEG_PATH:
            logger.warning("ffmpeg not available. Cannot load video.")
            return None
        
        # Check if video is already loaded
        if url in self.loaded_media:
            if callback:
                callback(url, self.loaded_media[url])
            return self.loaded_media[url]
        
        # Start a background thread to load the video
        thread = threading.Thread(
            target=self._load_video_thread,
            args=(url, callback),
            daemon=True
        )
        thread.start()
        
        return None
    
    def _load_video_thread(self, url: str, callback: Any) -> None:
        """
        Background thread for loading a video.
        
        Args:
            url: URL or path to the video
            callback: Optional callback function to call when video is loaded
        """
        try:
            # Check if this is a local file path or a URL
            if url.startswith(('http://', 'https://')):
                # Download the video
                cache_path = self._download_file(url)
                if not cache_path:
                    logger.error(f"Failed to download video: {url}")
                    return
            else:
                # Local file path
                if os.path.exists(url):
                    cache_path = url
                else:
                    logger.error(f"Video file not found: {url}")
                    return
            
            # Store in loaded media dictionary
            with self._lock:
                self.loaded_media[url] = cache_path
            
            # Get video information using ffmpeg
            video_info = self._get_video_info(cache_path)
            
            # Call the callback if provided
            if callback:
                callback(url, cache_path, video_info)
        except Exception as e:
            logger.error(f"Error in video loading thread for {url}: {e}")
    
    def load_audio(self, url: str, callback: Any = None) -> Optional[str]:
        """
        Load an audio file from a URL.
        
        Args:
            url: URL or path to the audio file
            callback: Optional callback function to call when audio is loaded
            
        Returns:
            Optional[str]: Path to the audio file or None if loading failed
        """
        if not self.enabled:
            logger.warning("Media handler is disabled")
            return None
        
        if not FFMPEG_PATH:
            logger.warning("ffmpeg not available. Cannot load audio.")
            return None
        
        # Check if audio is already loaded
        if url in self.loaded_media:
            if callback:
                callback(url, self.loaded_media[url])
            return self.loaded_media[url]
        
        # Start a background thread to load the audio
        thread = threading.Thread(
            target=self._load_audio_thread,
            args=(url, callback),
            daemon=True
        )
        thread.start()
        
        return None
    
    def _load_audio_thread(self, url: str, callback: Any) -> None:
        """
        Background thread for loading an audio file.
        
        Args:
            url: URL or path to the audio file
            callback: Optional callback function to call when audio is loaded
        """
        try:
            # Check if this is a local file path or a URL
            if url.startswith(('http://', 'https://')):
                # Download the audio file
                cache_path = self._download_file(url)
                if not cache_path:
                    logger.error(f"Failed to download audio: {url}")
                    return
            else:
                # Local file path
                if os.path.exists(url):
                    cache_path = url
                else:
                    logger.error(f"Audio file not found: {url}")
                    return
            
            # Store in loaded media dictionary
            with self._lock:
                self.loaded_media[url] = cache_path
            
            # Get audio information using ffmpeg
            audio_info = self._get_audio_info(cache_path)
            
            # Call the callback if provided
            if callback:
                callback(url, cache_path, audio_info)
        except Exception as e:
            logger.error(f"Error in audio loading thread for {url}: {e}")
    
    def _download_file(self, url: str) -> Optional[str]:
        """
        Download a file from a URL and cache it.
        
        Args:
            url: URL to download
            
        Returns:
            Optional[str]: Path to the cached file or None if download failed
        """
        try:
            # Check if download is already in progress
            with self._lock:
                if url in self.ongoing_downloads:
                    # Wait for the download to complete
                    while url in self.ongoing_downloads:
                        self._lock.release()
                        time.sleep(0.1)
                        self._lock.acquire()
                    
                    # If the download was successful, return the cached path
                    if url in self.loaded_media:
                        return self.loaded_media[url]
                    else:
                        return None
                
                # Mark this URL as being downloaded
                self.ongoing_downloads[url] = True
            
            # Generate a cache file path based on the URL
            url_hash = hashlib.md5(url.encode()).hexdigest()
            parsed_url = urllib.parse.urlparse(url)
            path = parsed_url.path
            filename = os.path.basename(path)
            
            if not filename:
                # If the URL doesn't have a filename, use the hash
                filename = url_hash
            else:
                # If the URL has a filename, prefix it with the hash to avoid collisions
                name, ext = os.path.splitext(filename)
                filename = f"{url_hash}{ext}"
            
            cache_path = os.path.join(self.cache_dir, filename)
            
            # Check if the file already exists in the cache
            if os.path.exists(cache_path):
                # Remove from ongoing downloads
                with self._lock:
                    if url in self.ongoing_downloads:
                        del self.ongoing_downloads[url]
                
                logger.debug(f"Using cached file for {url}: {cache_path}")
                return cache_path
            
            # Download the file
            logger.debug(f"Downloading {url} to {cache_path}")
            
            headers = {
                'User-Agent': 'WinkBrowser/0.1',
            }
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                with open(cache_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
            
            # Remove from ongoing downloads
            with self._lock:
                if url in self.ongoing_downloads:
                    del self.ongoing_downloads[url]
            
            logger.debug(f"Downloaded {url} to {cache_path}")
            return cache_path
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            
            # Remove from ongoing downloads
            with self._lock:
                if url in self.ongoing_downloads:
                    del self.ongoing_downloads[url]
            
            return None
    
    def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Get information about a video file using ffmpeg.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dict[str, Any]: Dictionary of video information
        """
        if not FFMPEG_PATH:
            return {}
        
        try:
            # Run ffprobe to get video information
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration,bit_rate,size:stream=width,height,codec_name,codec_type',
                '-of', 'default=noprint_wrappers=1',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stdout
            
            # Parse the output
            info = {}
            for line in output.splitlines():
                if '=' in line:
                    key, value = line.split('=', 1)
                    info[key.strip()] = value.strip()
            
            # Extract video and audio stream information
            video_info = {
                'path': video_path,
                'width': int(info.get('width', 0)),
                'height': int(info.get('height', 0)),
                'duration': float(info.get('duration', 0)),
                'bit_rate': int(info.get('bit_rate', 0)),
                'size': int(info.get('size', 0)),
                'video_codec': info.get('codec_name', ''),
                'audio_codec': '',  # Will be filled if audio stream is found
            }
            
            return video_info
        except Exception as e:
            logger.error(f"Error getting video info for {video_path}: {e}")
            return {}
    
    def _get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """
        Get information about an audio file using ffmpeg.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dict[str, Any]: Dictionary of audio information
        """
        if not FFMPEG_PATH:
            return {}
        
        try:
            # Run ffprobe to get audio information
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration,bit_rate,size:stream=codec_name,codec_type,channels,sample_rate',
                '-of', 'default=noprint_wrappers=1',
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stdout
            
            # Parse the output
            info = {}
            for line in output.splitlines():
                if '=' in line:
                    key, value = line.split('=', 1)
                    info[key.strip()] = value.strip()
            
            # Extract audio stream information
            audio_info = {
                'path': audio_path,
                'duration': float(info.get('duration', 0)),
                'bit_rate': int(info.get('bit_rate', 0)),
                'size': int(info.get('size', 0)),
                'audio_codec': info.get('codec_name', ''),
                'channels': int(info.get('channels', 0)),
                'sample_rate': int(info.get('sample_rate', 0)),
            }
            
            return audio_info
        except Exception as e:
            logger.error(f"Error getting audio info for {audio_path}: {e}")
            return {}
    
    def create_video_thumbnail(self, 
                               video_path: str, 
                               width: int = 320, 
                               height: int = 240) -> Optional[Any]:
        """
        Create a thumbnail for a video using ffmpeg.
        
        Args:
            video_path: Path to the video file
            width: Thumbnail width
            height: Thumbnail height
            
        Returns:
            Optional[Any]: Thumbnail image or None if creation failed
        """
        if not self.enabled:
            logger.warning("Media handler is disabled")
            return None
        
        if not FFMPEG_PATH:
            logger.warning("ffmpeg not available. Cannot create video thumbnail.")
            return None
        
        try:
            # Generate a temporary file for the thumbnail
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                thumbnail_path = tmp_file.name
            
            # Use ffmpeg to extract a frame from the middle of the video
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', '00:00:01.000',  # 1 second into the video
                '-vframes', '1',
                '-s', f'{width}x{height}',
                thumbnail_path
            ]
            
            subprocess.run(cmd, capture_output=True)
            
            # Load the thumbnail using PIL
            if os.path.exists(thumbnail_path):
                with Image.open(thumbnail_path) as img:
                    thumbnail = img.copy()
                
                # Clean up the temporary file
                os.unlink(thumbnail_path)
                
                return thumbnail
            else:
                logger.error(f"Failed to create thumbnail for {video_path}")
                return None
        except Exception as e:
            logger.error(f"Error creating video thumbnail for {video_path}: {e}")
            return None
    
    def clear_cache(self) -> None:
        """Clear the media cache."""
        try:
            # Remove all files in the cache directory
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    logger.error(f"Error deleting {file_path}: {e}")
            
            # Clear the loaded media dictionary
            with self._lock:
                self.loaded_media.clear()
            
            logger.debug("Media cache cleared")
        except Exception as e:
            logger.error(f"Error clearing media cache: {e}")
    
    def clean_up(self) -> None:
        """Clean up resources used by the media handler."""
        try:
            # Clear the loaded media dictionary
            with self._lock:
                self.loaded_media.clear()
            
            logger.debug("Media handler cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up media handler: {e}") 