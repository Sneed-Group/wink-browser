"""
Browser window implementation using Tkinter.
This module contains the main UI for the browser.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import webbrowser
import os
import threading
from typing import Callable, Optional, Dict, List, Any

from browser_engine.core.engine import BrowserEngine
from browser_engine.ui.renderer import TkRenderer
from browser_engine.ui.dialogs import SettingsDialog
from browser_engine.utils.config import Config

logger = logging.getLogger(__name__)

class BrowserWindow:
    """Main browser window implementation."""
    
    def __init__(self, engine: BrowserEngine):
        """
        Initialize the browser window.
        
        Args:
            engine: The browser engine to use
        """
        self.engine = engine
        self.config = Config()
        
        # Register for loading state changes
        self.engine.register_load_callback(self._on_load_state_changed)
        
        # Create the main window
        self.root = tk.Tk()
        self.root.title("Wink Browser")
        self.root.geometry("1024x768")
        self.root.minsize(800, 600)
        
        # Set up icons and theme
        self._setup_theme()
        
        # Create UI components
        self._create_menu()
        self._create_toolbar()
        self._create_statusbar()
        self._create_content_area()
        
        # Bind keyboard shortcuts
        self._bind_shortcuts()
        
        # Set up renderer
        self.renderer = TkRenderer(self.content_frame, self.engine)
        
        logger.info("Browser window initialized")
    
    def _setup_theme(self) -> None:
        """Set up the browser theme and icons."""
        # Try to use a modern theme if available
        try:
            self.style = ttk.Style()
            available_themes = self.style.theme_names()
            
            preferred_themes = ['clam', 'alt', 'default']
            for theme in preferred_themes:
                if theme in available_themes:
                    self.style.theme_use(theme)
                    break
            
            # Configure colors
            self.style.configure('TFrame', background='#f0f0f0')
            self.style.configure('TButton', background='#e0e0e0')
            self.style.configure('TEntry', fieldbackground='white')
            
        except Exception as e:
            logger.warning(f"Error setting up theme: {e}")
    
    def _create_menu(self) -> None:
        """Create the main menu bar."""
        self.menu_bar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="New Window", command=self._new_window)
        file_menu.add_command(label="New Private Window", command=self._new_private_window)
        file_menu.add_separator()
        file_menu.add_command(label="Open File", command=self._open_file)
        file_menu.add_command(label="Save Page As", command=self._save_page)
        file_menu.add_separator()
        file_menu.add_command(label="Print", command=self._print_page)
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self._close)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        edit_menu.add_command(label="Cut", command=lambda: self.root.focus_get().event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", command=lambda: self.root.focus_get().event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", command=lambda: self.root.focus_get().event_generate("<<Paste>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Find", command=self._find_in_page)
        self.menu_bar.add_cascade(label="Edit", menu=edit_menu)
        
        # View menu
        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        view_menu.add_command(label="Zoom In", command=self._zoom_in)
        view_menu.add_command(label="Zoom Out", command=self._zoom_out)
        view_menu.add_command(label="Reset Zoom", command=self._zoom_reset)
        view_menu.add_separator()
        
        # Create a checkbutton for text-only mode
        self.text_only_var = tk.BooleanVar(value=self.engine.text_only_mode)
        view_menu.add_checkbutton(
            label="Text-Only Mode", 
            variable=self.text_only_var,
            command=self._toggle_text_only_mode
        )
        
        view_menu.add_separator()
        view_menu.add_command(label="Page Source", command=self._view_source)
        self.menu_bar.add_cascade(label="View", menu=view_menu)
        
        # History menu
        history_menu = tk.Menu(self.menu_bar, tearoff=0)
        history_menu.add_command(label="Back", command=self._go_back)
        history_menu.add_command(label="Forward", command=self._go_forward)
        history_menu.add_separator()
        history_menu.add_command(label="Home", command=self._go_home)
        self.menu_bar.add_cascade(label="History", menu=history_menu)
        
        # Privacy menu
        privacy_menu = tk.Menu(self.menu_bar, tearoff=0)
        
        # Create a checkbutton for private browsing
        self.private_mode_var = tk.BooleanVar(value=self.engine.private_mode)
        privacy_menu.add_checkbutton(
            label="Private Browsing", 
            variable=self.private_mode_var,
            command=self._toggle_private_mode
        )
        
        privacy_menu.add_separator()
        privacy_menu.add_command(label="Clear Browsing Data", command=self._clear_data)
        privacy_menu.add_separator()
        privacy_menu.add_command(label="Ad Blocker Settings", command=self._ad_blocker_settings)
        self.menu_bar.add_cascade(label="Privacy", menu=privacy_menu)
        
        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=self.menu_bar)
    
    def _create_toolbar(self) -> None:
        """Create the browser toolbar with navigation buttons and address bar."""
        self.toolbar_frame = ttk.Frame(self.root)
        self.toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Navigation buttons
        self.back_button = ttk.Button(self.toolbar_frame, text="←", width=2, command=self._go_back)
        self.back_button.pack(side=tk.LEFT, padx=2)
        
        self.forward_button = ttk.Button(self.toolbar_frame, text="→", width=2, command=self._go_forward)
        self.forward_button.pack(side=tk.LEFT, padx=2)
        
        self.refresh_button = ttk.Button(self.toolbar_frame, text="↻", width=2, command=self._refresh)
        self.refresh_button.pack(side=tk.LEFT, padx=2)
        
        self.home_button = ttk.Button(self.toolbar_frame, text="⌂", width=2, command=self._go_home)
        self.home_button.pack(side=tk.LEFT, padx=2)
        
        # Address bar
        self.url_var = tk.StringVar()
        self.address_bar = ttk.Entry(self.toolbar_frame, textvariable=self.url_var)
        self.address_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.address_bar.bind("<Return>", self._on_address_enter)
        
        # Search bar
        self.search_button = ttk.Button(self.toolbar_frame, text="🔍", width=2, command=self._search)
        self.search_button.pack(side=tk.LEFT, padx=2)
        
        # Settings button
        self.settings_button = ttk.Button(self.toolbar_frame, text="⚙", width=2, command=self._show_settings)
        self.settings_button.pack(side=tk.LEFT, padx=2)
    
    def _create_statusbar(self) -> None:
        """Create the status bar at the bottom of the window."""
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Status label on the left
        self.status_label = ttk.Label(self.status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Progress bar in the middle
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self.status_frame, 
            variable=self.progress_var,
            mode='determinate', 
            length=200
        )
        self.progress_bar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Mode indicators on the right
        self.text_mode_label = ttk.Label(self.status_frame, text="")
        self.text_mode_label.pack(side=tk.RIGHT, padx=5)
        
        self.private_mode_label = ttk.Label(self.status_frame, text="")
        self.private_mode_label.pack(side=tk.RIGHT, padx=5)
        
        self._update_mode_indicators()
    
    def _create_content_area(self) -> None:
        """Create the main content area for displaying web pages."""
        self.content_frame = ttk.Frame(self.root)
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    
    def _bind_shortcuts(self) -> None:
        """Bind keyboard shortcuts."""
        self.root.bind("<Control-n>", lambda e: self._new_window())
        self.root.bind("<Control-Shift-n>", lambda e: self._new_private_window())
        self.root.bind("<Control-o>", lambda e: self._open_file())
        self.root.bind("<Control-s>", lambda e: self._save_page())
        self.root.bind("<Control-p>", lambda e: self._print_page())
        self.root.bind("<Control-q>", lambda e: self._close())
        
        self.root.bind("<Control-f>", lambda e: self._find_in_page())
        
        self.root.bind("<Control-plus>", lambda e: self._zoom_in())
        self.root.bind("<Control-minus>", lambda e: self._zoom_out())
        self.root.bind("<Control-0>", lambda e: self._zoom_reset())
        
        self.root.bind("<Control-j>", lambda e: self._toggle_text_only_mode())
        
        self.root.bind("<Alt-Left>", lambda e: self._go_back())
        self.root.bind("<Alt-Right>", lambda e: self._go_forward())
        self.root.bind("<F5>", lambda e: self._refresh())
    
    def _on_address_enter(self, event=None) -> None:
        """Handle Enter key in the address bar."""
        url = self.url_var.get().strip()
        if url:
            self.navigate_to(url)
    
    def _update_mode_indicators(self) -> None:
        """Update the status bar mode indicators."""
        if self.engine.text_only_mode:
            self.text_mode_label.config(text="Text-Only Mode")
        else:
            self.text_mode_label.config(text="")
            
        if self.engine.private_mode:
            self.private_mode_label.config(text="Private Browsing")
        else:
            self.private_mode_label.config(text="")
    
    def _on_load_state_changed(self) -> None:
        """Handle loading state changes."""
        if self.engine.is_loading:
            self.status_label.config(text="Loading...")
            self.refresh_button.config(text="✕")  # Change to stop button
            self.progress_var.set(self.engine.load_progress)
        else:
            if self.engine.current_url:
                self.status_label.config(text=f"Loaded: {self.engine.current_url}")
                self.url_var.set(self.engine.current_url)
                self.root.title(f"{self.engine.page_title} - Wink Browser")
            else:
                self.status_label.config(text="Ready")
                self.root.title("Wink Browser")
                
            self.refresh_button.config(text="↻")  # Change back to refresh button
            self.progress_var.set(0)
            
        # Update the content view
        self.renderer.update()
    
    def navigate_to(self, url: str) -> None:
        """
        Navigate to a URL.
        
        Args:
            url: The URL to navigate to
        """
        self.engine.load_url(url)
    
    def _go_back(self) -> None:
        """Navigate back in history."""
        self.engine.go_back()
    
    def _go_forward(self) -> None:
        """Navigate forward in history."""
        self.engine.go_forward()
    
    def _refresh(self) -> None:
        """Refresh the current page or stop loading."""
        if self.engine.is_loading:
            self.engine.stop_loading()
        else:
            self.engine.refresh()
    
    def _go_home(self) -> None:
        """Navigate to the home page."""
        home_url = self.config.get("browser.home_page", "https://www.example.com")
        self.navigate_to(home_url)
    
    def _toggle_text_only_mode(self) -> None:
        """Toggle text-only mode."""
        new_state = self.text_only_var.get()
        self.engine.set_text_only_mode(new_state)
        self._update_mode_indicators()
    
    def _toggle_private_mode(self) -> None:
        """Toggle private browsing mode."""
        new_state = self.private_mode_var.get()
        self.engine.set_private_mode(new_state)
        self._update_mode_indicators()
    
    def _new_window(self) -> None:
        """Open a new browser window."""
        # In a real implementation, we would create a new browser window
        messagebox.showinfo("New Window", "This would open a new browser window.")
    
    def _new_private_window(self) -> None:
        """Open a new private browser window."""
        # In a real implementation, we would create a new private browser window
        messagebox.showinfo("New Private Window", "This would open a new private browser window.")
    
    def _open_file(self) -> None:
        """Open a local HTML file."""
        file_path = filedialog.askopenfilename(
            title="Open File",
            filetypes=[
                ("HTML Files", "*.html;*.htm"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            file_url = f"file://{os.path.abspath(file_path)}"
            self.navigate_to(file_url)
    
    def _save_page(self) -> None:
        """Save the current page to a file."""
        if not self.engine.current_url:
            messagebox.showinfo("Save Page", "No page to save.")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Save Page As",
            defaultextension=".html",
            filetypes=[
                ("HTML Files", "*.html"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.engine.get_rendered_content())
                messagebox.showinfo("Save Page", "Page saved successfully.")
            except Exception as e:
                messagebox.showerror("Save Page", f"Error saving page: {e}")
    
    def _print_page(self) -> None:
        """Print the current page."""
        messagebox.showinfo("Print", "Printing is not implemented in this demo.")
    
    def _find_in_page(self) -> None:
        """Find text in the current page."""
        # In a real implementation, we would show a find dialog
        messagebox.showinfo("Find", "Find in page is not implemented in this demo.")
    
    def _zoom_in(self) -> None:
        """Zoom in the current page."""
        self.renderer.zoom_in()
    
    def _zoom_out(self) -> None:
        """Zoom out the current page."""
        self.renderer.zoom_out()
    
    def _zoom_reset(self) -> None:
        """Reset zoom to default level."""
        self.renderer.zoom_reset()
    
    def _view_source(self) -> None:
        """View the source code of the current page."""
        if not self.engine.current_url:
            messagebox.showinfo("View Source", "No page to view source.")
            return
            
        # Create a new window for the source view
        source_window = tk.Toplevel(self.root)
        source_window.title(f"Source: {self.engine.current_url}")
        source_window.geometry("800x600")
        
        # Create a text widget with scrollbar
        text_frame = ttk.Frame(source_window)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget = tk.Text(text_frame, wrap=tk.NONE, yscrollcommand=scrollbar.set)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=text_widget.yview)
        
        # Insert the source code
        text_widget.insert(tk.END, self.engine.get_rendered_content())
        text_widget.config(state=tk.DISABLED)  # Make it read-only
    
    def _search(self) -> None:
        """Perform a web search."""
        query = self.url_var.get().strip()
        if query:
            if ' ' in query and not query.startswith(('http://', 'https://')):
                # This looks like a search query
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                self.navigate_to(search_url)
            else:
                # This might be a URL
                self.navigate_to(query)
    
    def _show_settings(self) -> None:
        """Show the settings dialog."""
        # In a real implementation, we would show a settings dialog
        messagebox.showinfo("Settings", "Settings dialog is not implemented in this demo.")
    
    def _clear_data(self) -> None:
        """Clear browsing data."""
        # In a real implementation, we would clear browsing data
        messagebox.showinfo("Clear Data", "This would clear browsing data.")
    
    def _ad_blocker_settings(self) -> None:
        """Show ad blocker settings."""
        # In a real implementation, we would show ad blocker settings
        messagebox.showinfo("Ad Blocker", "Ad blocker settings are not implemented in this demo.")
    
    def _show_about(self) -> None:
        """Show the about dialog."""
        messagebox.showinfo(
            "About Wink Browser",
            "Wink Browser\nVersion 0.1.0\n\n"
            "A privacy-focused web browser with its own rendering engine.\n\n"
            "Copyright © 2023 Wink Browser Team"
        )
    
    def _close(self) -> None:
        """Close the browser window."""
        self.root.destroy()
    
    def start(self) -> None:
        """Start the main UI loop."""
        self.root.mainloop() 