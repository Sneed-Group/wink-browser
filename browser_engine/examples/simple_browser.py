#!/usr/bin/env python3
"""
Simple Browser Example

This example demonstrates how to use the HTML5Engine to create a simple browser.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from urllib.parse import urlparse

# Add the parent directory to the path so we can import the browser_engine package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from browser_engine.html5_engine import HTML5Engine

class SimpleBrowser:
    """A simple browser application using the HTML5Engine."""
    
    def __init__(self, root):
        """
        Initialize the browser application.
        
        Args:
            root: The Tkinter root window
        """
        self.root = root
        self.root.title("Simple HTML5 Browser")
        self.root.geometry("1024x768")
        
        # Create the UI
        self._create_ui()
        
        # Initialize the HTML5 engine
        self.engine = HTML5Engine(
            width=self.content_frame.winfo_width() or 800,
            height=self.content_frame.winfo_height() or 600,
            debug=True
        )
        
        # Register event handlers
        self.engine.on_load(self._on_page_loaded)
        self.engine.on_error(self._on_error)
        
        # Add the renderer to the content frame
        self.engine.renderer.frame.pack(fill=tk.BOTH, expand=True)
        
        # Load a default page
        self._load_default_page()
    
    def _create_ui(self):
        """Create the user interface."""
        # Create the main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create the toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # Back button
        self.back_button = ttk.Button(toolbar, text="←", width=3, command=self._go_back)
        self.back_button.pack(side=tk.LEFT, padx=2)
        
        # Forward button
        self.forward_button = ttk.Button(toolbar, text="→", width=3, command=self._go_forward)
        self.forward_button.pack(side=tk.LEFT, padx=2)
        
        # Refresh button
        self.refresh_button = ttk.Button(toolbar, text="↻", width=3, command=self._refresh)
        self.refresh_button.pack(side=tk.LEFT, padx=2)
        
        # URL entry
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(toolbar, textvariable=self.url_var)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.url_entry.bind("<Return>", self._on_url_enter)
        
        # Go button
        self.go_button = ttk.Button(toolbar, text="Go", command=self._on_go_click)
        self.go_button.pack(side=tk.LEFT, padx=2)
        
        # Open file button
        self.open_button = ttk.Button(toolbar, text="Open", command=self._on_open_click)
        self.open_button.pack(side=tk.LEFT, padx=2)
        
        # Create the content frame
        self.content_frame = ttk.Frame(main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create the status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var, anchor=tk.W, relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)
        
        # Initialize history
        self.history = []
        self.current_history_index = -1
        
        # Update UI state
        self._update_navigation_buttons()
    
    def _load_default_page(self):
        """Load a default welcome page."""
        default_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Welcome to Simple Browser</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 40px;
                    line-height: 1.6;
                }
                h1 {
                    color: #4285f4;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    border: 1px solid #e0e0e0;
                    border-radius: 5px;
                    background-color: #f9f9f9;
                }
                .url-example {
                    font-family: monospace;
                    background-color: #f0f0f0;
                    padding: 5px;
                    border-radius: 3px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Welcome to Simple Browser</h1>
                <p>This is a simple browser built with the HTML5Engine.</p>
                <h2>Getting Started</h2>
                <p>You can:</p>
                <ul>
                    <li>Enter a URL in the address bar and press Enter or click Go</li>
                    <li>Open a local HTML file using the Open button</li>
                    <li>Navigate back and forward using the arrow buttons</li>
                </ul>
                <p>Try loading a website like <span class="url-example">https://example.com</span></p>
            </div>
        </body>
        </html>
        """
        self.engine.load_html(default_html, "about:welcome")
        self.url_var.set("about:welcome")
    
    def _on_url_enter(self, event):
        """Handle URL entry."""
        self._navigate_to_url()
    
    def _on_go_click(self):
        """Handle Go button click."""
        self._navigate_to_url()
    
    def _on_open_click(self):
        """Handle Open button click."""
        file_path = filedialog.askopenfilename(
            title="Open HTML File",
            filetypes=[("HTML Files", "*.html;*.htm"), ("All Files", "*.*")]
        )
        
        if file_path:
            try:
                self.status_var.set(f"Loading file: {file_path}")
                self.root.update_idletasks()
                
                # Load the file
                self.engine.load_file(file_path)
                
                # Update URL entry
                self.url_var.set(f"file://{os.path.abspath(file_path)}")
                
                # Add to history
                self._add_to_history(self.url_var.get())
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")
                self.status_var.set("Error loading file")
    
    def _navigate_to_url(self):
        """Navigate to the URL in the entry field."""
        url = self.url_var.get().strip()
        
        # Add http:// if no protocol specified and not a file path
        if not url.startswith(("http://", "https://", "file://", "about:")) and not os.path.exists(url):
            url = f"http://{url}"
            self.url_var.set(url)
        
        try:
            self.status_var.set(f"Loading: {url}")
            self.root.update_idletasks()
            
            # Load the URL
            if url.startswith("file://"):
                # Extract the file path from the URL
                parsed_url = urlparse(url)
                file_path = parsed_url.path
                
                # On Windows, remove the leading slash
                if sys.platform == 'win32' and file_path.startswith('/'):
                    file_path = file_path[1:]
                
                self.engine.load_file(file_path)
            elif url.startswith("about:"):
                # Handle about: URLs
                if url == "about:welcome":
                    self._load_default_page()
                else:
                    self.status_var.set(f"Unknown about: URL: {url}")
            else:
                # Load from web
                self.engine.load_url(url)
            
            # Add to history
            self._add_to_history(url)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load URL: {str(e)}")
            self.status_var.set("Error loading URL")
    
    def _go_back(self):
        """Navigate back in history."""
        if self.current_history_index > 0:
            self.current_history_index -= 1
            url = self.history[self.current_history_index]
            
            # Update URL without adding to history
            self.url_var.set(url)
            self._navigate_to_url_without_history(url)
            
            # Update navigation buttons
            self._update_navigation_buttons()
    
    def _go_forward(self):
        """Navigate forward in history."""
        if self.current_history_index < len(self.history) - 1:
            self.current_history_index += 1
            url = self.history[self.current_history_index]
            
            # Update URL without adding to history
            self.url_var.set(url)
            self._navigate_to_url_without_history(url)
            
            # Update navigation buttons
            self._update_navigation_buttons()
    
    def _refresh(self):
        """Refresh the current page."""
        current_url = self.url_var.get()
        if current_url:
            self._navigate_to_url_without_history(current_url)
    
    def _navigate_to_url_without_history(self, url):
        """Navigate to a URL without adding to history."""
        try:
            self.status_var.set(f"Loading: {url}")
            self.root.update_idletasks()
            
            # Load the URL
            if url.startswith("file://"):
                # Extract the file path from the URL
                parsed_url = urlparse(url)
                file_path = parsed_url.path
                
                # On Windows, remove the leading slash
                if sys.platform == 'win32' and file_path.startswith('/'):
                    file_path = file_path[1:]
                
                self.engine.load_file(file_path)
            elif url.startswith("about:"):
                # Handle about: URLs
                if url == "about:welcome":
                    self._load_default_page()
                else:
                    self.status_var.set(f"Unknown about: URL: {url}")
            else:
                # Load from web
                self.engine.load_url(url)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load URL: {str(e)}")
            self.status_var.set("Error loading URL")
    
    def _add_to_history(self, url):
        """Add a URL to the browsing history."""
        # If we're not at the end of the history, truncate it
        if self.current_history_index < len(self.history) - 1:
            self.history = self.history[:self.current_history_index + 1]
        
        # Add the URL to history
        self.history.append(url)
        self.current_history_index = len(self.history) - 1
        
        # Update navigation buttons
        self._update_navigation_buttons()
    
    def _update_navigation_buttons(self):
        """Update the state of navigation buttons."""
        # Update back button
        if self.current_history_index > 0:
            self.back_button.state(['!disabled'])
        else:
            self.back_button.state(['disabled'])
        
        # Update forward button
        if self.current_history_index < len(self.history) - 1:
            self.forward_button.state(['!disabled'])
        else:
            self.forward_button.state(['disabled'])
    
    def _on_page_loaded(self):
        """Handle page loaded event."""
        if self.engine.document and hasattr(self.engine.document, 'title'):
            title = self.engine.document.title or "Untitled"
            self.root.title(f"{title} - Simple HTML5 Browser")
        
        self.status_var.set("Page loaded")
    
    def _on_error(self, error_message):
        """Handle error event."""
        self.status_var.set(f"Error: {error_message}")


def main():
    """Main entry point for the application."""
    root = tk.Tk()
    app = SimpleBrowser(root)
    root.mainloop()


if __name__ == "__main__":
    main() 