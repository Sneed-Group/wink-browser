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
import io
import cssutils
from typing import Callable, Optional, Dict, List, Any

from browser_engine.html5_engine import HTML5Engine
from browser_engine.html5_engine.rendering import HTML5Renderer
from browser_engine.ui.dialogs import SettingsDialog
from browser_engine.utils.config_manager import ConfigManager
from browser_engine.utils.url import URL
from browser_engine.network.network_manager import NetworkManager
from browser_engine.privacy.ad_blocker import AdBlocker
from browser_engine.extensions.extension_manager import ExtensionManager
from browser_engine.utils.profile_manager import ProfileManager

# Suppress cssutils logging
cssutils.log.setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

class BrowserWindow:
    """Main browser window implementation."""
    
    def __init__(self, root, network_manager, ad_blocker, 
                 extension_manager, profile_manager, config_manager,
                 disable_javascript=False, private_mode=False, debug_mode=False):
        """
        Initialize the browser window.
        
        Args:
            root: The root Tk window
            network_manager: Network request manager
            ad_blocker: Ad blocking component
            extension_manager: Browser extension manager
            profile_manager: User profile manager
            config_manager: Browser configuration manager
            disable_javascript: Whether to disable JavaScript
            private_mode: Whether to use private browsing mode
            debug_mode: Whether to enable debug logging
        """
        self.root = root
        self.network_manager = network_manager
        self.ad_blocker = ad_blocker
        self.extension_manager = extension_manager
        self.profile_manager = profile_manager
        self.config_manager = config_manager
        self.disable_javascript = disable_javascript
        self.private_mode = private_mode
        self.debug_mode = debug_mode
        
        # Browser state
        self.history = []
        self.current_history_index = -1
        self.is_loading = False
        self.current_url = None
        self.content_cache = {}
        
        # Initialize the HTML5 rendering engine
        self.html5_engine = HTML5Engine(
            width=self.root.winfo_width(), 
            height=self.root.winfo_height(), 
            debug=self.debug_mode
        )
        
        # Register for loading state changes
        self.html5_engine.on_load(self._on_page_loaded)
        self.html5_engine.on_error(self._on_page_error)
        
        # Set up icons and theme
        self._setup_theme()
        
        # Create UI components
        self._create_menu()
        self._create_toolbar()
        self._create_statusbar()
        self._create_content_area()
        
        # Bind keyboard shortcuts
        self._bind_shortcuts()
        
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
        self.text_only_var = tk.BooleanVar(value=self.disable_javascript)
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
        self.private_mode_var = tk.BooleanVar(value=self.private_mode)
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
        
        # Initialize the HTML5 renderer with our content frame
        self.html5_engine.initialize_renderer(self.content_frame)
        self.renderer = self.html5_engine.renderer
        
        # Set up link click handler
        self.renderer.on_link_click = self._on_link_click
    
    def _bind_shortcuts(self) -> None:
        """Bind keyboard shortcuts for common actions."""
        # Navigation shortcuts
        self.root.bind("<Alt-Left>", lambda e: self._go_back())
        self.root.bind("<Alt-Right>", lambda e: self._go_forward())
        self.root.bind("<F5>", lambda e: self._refresh())
        self.root.bind("<Control-r>", lambda e: self._refresh())
        self.root.bind("<Alt-Home>", lambda e: self._go_home())
        
        # Tab management
        self.root.bind("<Control-t>", lambda e: self._new_window())
        self.root.bind("<Control-w>", lambda e: self._close())
        
        # Find in page
        self.root.bind("<Control-f>", lambda e: self._find_in_page())
        
        # Zoom controls
        self.root.bind("<Control-plus>", lambda e: self._zoom_in())
        self.root.bind("<Control-minus>", lambda e: self._zoom_out())
        self.root.bind("<Control-0>", lambda e: self._zoom_reset())
        
        # Developer tools
        self.root.bind("<F12>", lambda e: self._view_source())
    
    def _on_address_enter(self, event=None) -> None:
        """Handle address bar enter key press."""
        url = self.url_var.get().strip()
        if url:
            self.navigate_to_url(url)
    
    def _on_link_click(self, url: str) -> None:
        """Handle link click events."""
        self.navigate_to_url(url)
    
    def _update_mode_indicators(self) -> None:
        """Update the mode indicator labels."""
        # Update text-only mode indicator
        if self.disable_javascript:
            self.text_mode_label.config(text="Text Mode")
        else:
            self.text_mode_label.config(text="")
        
        # Update private mode indicator
        if self.private_mode:
            self.private_mode_label.config(text="Private")
        else:
            self.private_mode_label.config(text="")
    
    def _on_page_loaded(self) -> None:
        """Handle page loaded event."""
        self.is_loading = False
        
        # Update UI
        self.status_label.config(text="Loaded")
        self.progress_var.set(100)
        self.refresh_button.config(text="↻")
        
        # Update title if available
        if self.html5_engine.document and self.html5_engine.document.title:
            self.root.title(f"{self.html5_engine.document.title} - Wink Browser")
    
    def _on_page_error(self, error_message: str) -> None:
        """Handle page error event."""
        self.is_loading = False
        
        # Update UI
        self.status_label.config(text=f"Error: {error_message}")
        self.progress_var.set(0)
        self.refresh_button.config(text="↻")
    
    def navigate_to_url(self, url: str) -> None:
        """
        Navigate to the specified URL.
        
        Args:
            url: URL to navigate to
        """
        # Check if URL is None
        if url is None:
            error_message = "Cannot navigate to None URL"
            logger.error(error_message)
            self.status_label.config(text=f"Error: {error_message}")
            return
            
        # Normalize and validate URL
        url_obj = URL(url)
        normalized_url = url_obj.normalized
        
        # Update address bar
        self.url_var.set(normalized_url)
        
        # Update status
        self.status_label.config(text=f"Loading {normalized_url}...")
        self.progress_var.set(20)
        self.is_loading = True
        
        # Change refresh button to stop button during loading
        self.refresh_button.config(text="✕")
        
        # Update history if this is a new navigation (not back/forward)
        if self.current_history_index == len(self.history) - 1:
            # Add to history
            self.history.append(normalized_url)
            self.current_history_index += 1
        elif self.current_history_index < len(self.history) - 1:
            # Navigating after using back button, remove forward history
            self.history = self.history[:self.current_history_index + 1]
            self.history.append(normalized_url)
            self.current_history_index += 1
        
        # Update navigation buttons
        self._update_navigation_state()
        
        # Set current URL
        self.current_url = normalized_url
        
        # Check if URL is in cache
        if normalized_url in self.content_cache and not self.private_mode:
            # Load from cache
            cached_content = self.content_cache[normalized_url]
            self._load_content_from_cache(cached_content)
            return
        
        # Start a new thread for loading
        threading.Thread(
            target=self._load_url_in_thread, 
            args=(normalized_url,),
            daemon=True
        ).start()
    
    def _load_url_in_thread(self, url: str) -> None:
        """
        Load URL in a separate thread to avoid UI freezing.
        
        Args:
            url: URL to load
        """
        try:
            # Check if URL is None
            if url is None:
                error_message = "Cannot load None URL"
                logger.error(error_message)
                self.root.after(0, lambda msg=error_message: self._on_page_error(msg))
                return
            
            # Apply ad blocker if enabled
            url = self.ad_blocker.process_url(url) if self.ad_blocker else url
            
            # Check if it's a special URL (about:, data:, etc.)
            url_obj = URL(url)
            
            # Debug: Print URL being loaded
            logger.debug(f"Loading URL in thread: {url}")
            
            # Use the HTML5 engine to load the URL
            success = self.html5_engine.load_url(url)
            
            # Debug: Print result of load_url
            logger.debug(f"URL load success: {success}")
            
            # Debug: Check document state
            if self.html5_engine.document:
                logger.debug(f"Document loaded: {self.html5_engine.document is not None}")
                logger.debug(f"Document has document_element: {hasattr(self.html5_engine.document, 'document_element') and self.html5_engine.document.document_element is not None}")
                
                if hasattr(self.html5_engine.document, 'document_element') and self.html5_engine.document.document_element is not None:
                    logger.debug(f"Document element tag: {self.html5_engine.document.document_element.tag_name}")
                    
                    # Check for head and body
                    head = self.html5_engine.document.querySelector("head")
                    body = self.html5_engine.document.querySelector("body")
                    logger.debug(f"Document has head: {head is not None}")
                    logger.debug(f"Document has body: {body is not None}")
                    
                    # Check for title
                    title = self.html5_engine.document.querySelector("title")
                    logger.debug(f"Document has title: {title is not None}")
                    if title:
                        logger.debug(f"Title text: {title.textContent}")
            
            if not success:
                error_message = f"Failed to load URL: {url}"
                logger.error(error_message)
                self.root.after(0, lambda msg=error_message: self._on_page_error(msg))
                return
                
            # Update progress
            self.root.after(0, lambda: self.progress_var.set(100))
            
            # Update renderer
            self.root.after(0, lambda: self._update_renderer())
            
            # Cache content if not in private mode and not a special URL
            if not self.private_mode and not url_obj.is_special:
                self.content_cache[url] = {
                    'document': self.html5_engine.document,
                    'layout': self.html5_engine.layout_engine
                }
            
        except Exception as e:
            logger.error(f"Error loading URL: {e}")
            error_message = str(e)
            self.root.after(0, lambda msg=error_message: self._on_page_error(msg))
    
    def _load_content_from_cache(self, cached_content: Dict) -> None:
        """
        Load content from cache.
        
        Args:
            cached_content: Cached content dict
        """
        # Set document and layout from cache
        self.html5_engine.document = cached_content['document']
        self.html5_engine.layout_engine = cached_content['layout']
        
        # Update renderer
        self._update_renderer()
        
        # Update UI
        self._on_page_loaded()
    
    def _update_renderer(self) -> None:
        """Update the renderer with the current document."""
        if self.html5_engine.document:
            # Safely get base_url, defaulting to an empty string if None
            base_url = self.html5_engine.base_url or ""
            logger.debug(f"Updating renderer with document from URL: {base_url}")
            
            # Make sure the renderer has the correct URL
            if hasattr(self.html5_engine.renderer, 'current_url'):
                self.html5_engine.renderer.current_url = base_url
                
            # Make sure we reset any about:blank state that might be interfering
            if base_url != "about:blank" and hasattr(self.html5_engine.renderer, 'document'):
                self.html5_engine.renderer.document = self.html5_engine.document
            
            # Use the new direct elements rendering approach
            try:
                # Get head and body elements directly
                head = self.html5_engine.document.querySelector("head")
                body = self.html5_engine.document.querySelector("body")
                
                logger.debug(f"Using direct elements rendering approach")
                logger.debug(f"Found head element: {head is not None}")
                logger.debug(f"Found body element: {body is not None}")
                
                if body:
                    # Use the direct rendering approach
                    self.html5_engine.renderer.render_elements(head, body, base_url)
                else:
                    # Fall back to the old approach if body not found
                    logger.warning("Could not find body element, falling back to document rendering")
                    self.html5_engine.renderer.render(self.html5_engine.document)
            except Exception as e:
                logger.error(f"Error using direct elements rendering: {e}")
                # Fall back to normal rendering if direct approach fails
                self.html5_engine.renderer.render(self.html5_engine.document)
    
    def _update_navigation_state(self) -> None:
        """Update navigation buttons based on history state."""
        # Update back button
        if self.current_history_index > 0:
            self.back_button.config(state=tk.NORMAL)
        else:
            self.back_button.config(state=tk.DISABLED)
        
        # Update forward button
        if self.current_history_index < len(self.history) - 1:
            self.forward_button.config(state=tk.NORMAL)
        else:
            self.forward_button.config(state=tk.DISABLED)
    
    def load_homepage(self) -> None:
        """Load the configured homepage."""
        homepage = self.config_manager.get('browser', 'homepage')
        self.navigate_to_url(homepage)
    
    def _go_back(self) -> None:
        """Navigate back in history."""
        if self.current_history_index > 0:
            self.current_history_index -= 1
            url = self.history[self.current_history_index]
            self.url_var.set(url)
            self.navigate_to_url(url)
            self._update_navigation_state()
    
    def _go_forward(self) -> None:
        """Navigate forward in history."""
        if self.current_history_index < len(self.history) - 1:
            self.current_history_index += 1
            url = self.history[self.current_history_index]
            self.url_var.set(url)
            self.navigate_to_url(url)
            self._update_navigation_state()
    
    def _refresh(self) -> None:
        """Refresh the current page."""
        if self.is_loading:
            # Stop loading
            self.is_loading = False
            self.status_label.config(text="Stopped")
            self.refresh_button.config(text="↻")
        else:
            # Refresh the page
            if self.current_url:
                # Remove from cache to force reload
                if self.current_url in self.content_cache:
                    del self.content_cache[self.current_url]
                
                self.navigate_to_url(self.current_url)
    
    def _go_home(self) -> None:
        """Navigate to homepage."""
        self.load_homepage()
    
    def _toggle_text_only_mode(self) -> None:
        """Toggle text-only (JavaScript disabled) mode."""
        self.disable_javascript = self.text_only_var.get()
        self._update_mode_indicators()
        
        # Refresh current page if needed
        if self.current_url:
            self._refresh()
    
    def _toggle_private_mode(self) -> None:
        """Toggle private browsing mode."""
        self.private_mode = self.private_mode_var.get()
        self._update_mode_indicators()
        
        # Clear cache if entering private mode
        if self.private_mode:
            self.content_cache.clear()
    
    def _new_window(self) -> None:
        """Open a new browser window."""
        # This should be implemented by the main app
        pass
    
    def _new_private_window(self) -> None:
        """Open a new private browser window."""
        # This should be implemented by the main app
        pass
    
    def _open_file(self) -> None:
        """Open a local HTML file."""
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("HTML files", "*.html;*.htm"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                self.html5_engine.load_file(file_path)
                self._update_renderer()
                self._on_page_loaded()
                
                # Update address bar with file URL
                file_url = f"file://{os.path.abspath(file_path)}"
                self.url_var.set(file_url)
                
            except Exception as e:
                logger.error(f"Error opening file: {e}")
                self._on_page_error(str(e))
    
    def _save_page(self) -> None:
        """Save the current page to a local file."""
        if not self.html5_engine.document:
            messagebox.showinfo("Save Page", "No page to save.")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[
                ("HTML files", "*.html"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                # Get the HTML content
                if hasattr(self.html5_engine.document, 'prettify'):
                    # BeautifulSoup document
                    html_content = self.html5_engine.document.prettify()
                else:
                    # Custom document with serialization
                    html_content = self.html5_engine.document.serialize()
                
                # Write to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                    
                messagebox.showinfo("Save Page", "Page saved successfully.")
                
            except Exception as e:
                logger.error(f"Error saving page: {e}")
                messagebox.showerror("Save Page", f"Error saving page: {str(e)}")
    
    def _print_page(self) -> None:
        """Print the current page."""
        messagebox.showinfo("Print", "Printing not implemented yet.")
    
    def _find_in_page(self) -> None:
        """Open find in page dialog."""
        messagebox.showinfo("Find", "Find in page not implemented yet.")
    
    def _zoom_in(self) -> None:
        """Zoom in the page view."""
        self.renderer.zoom_in()
        self._update_renderer()
    
    def _zoom_out(self) -> None:
        """Zoom out the page view."""
        self.renderer.zoom_out()
        self._update_renderer()
    
    def _zoom_reset(self) -> None:
        """Reset zoom to default level."""
        self.renderer.zoom_reset()
        self._update_renderer()
    
    def _view_source(self) -> None:
        """View the source code of the current page."""
        if not self.html5_engine.document:
            messagebox.showinfo("View Source", "No page to view source.")
            return
        
        # Create a new window for the source view
        source_window = tk.Toplevel(self.root)
        source_window.title("Page Source")
        source_window.geometry("800x600")
        
        # Create a text widget with scrollbars
        source_frame = ttk.Frame(source_window)
        source_frame.pack(fill=tk.BOTH, expand=True)
        
        v_scrollbar = ttk.Scrollbar(source_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scrollbar = ttk.Scrollbar(source_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        source_text = tk.Text(
            source_frame,
            wrap=tk.NONE,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            font=("Courier", 12)
        )
        source_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        v_scrollbar.config(command=source_text.yview)
        h_scrollbar.config(command=source_text.xview)
        
        # Get the HTML content
        if hasattr(self.html5_engine.document, 'prettify'):
            # BeautifulSoup document
            html_content = self.html5_engine.document.prettify()
        else:
            # Custom document with serialization
            html_content = self.html5_engine.document.serialize()
        
        # Insert the content
        source_text.insert(tk.END, html_content)
        source_text.config(state=tk.DISABLED)
    
    def _search(self) -> None:
        """Perform a web search."""
        search_terms = self.url_var.get().strip()
        
        if not search_terms:
            return
            
        # Check if the input is a URL
        if URL(search_terms).is_valid:
            self.navigate_to_url(search_terms)
            return
            
        # Otherwise, treat as search terms
        search_engine = self.config_manager.get('browser', 'search_engine')
        search_template = self.config_manager.get('browser', 'search_template')
        
        # Format the search URL
        search_url = search_template.replace('{searchTerms}', search_terms)
        
        # Navigate to the search URL
        self.navigate_to_url(search_url)
    
    def _show_settings(self) -> None:
        """Show settings dialog."""
        dialog = SettingsDialog(self.root, self.config_manager)
        dialog.show()
    
    def _clear_data(self) -> None:
        """Clear browsing data."""
        # Clear the content cache
        self.content_cache.clear()
        messagebox.showinfo("Privacy", "Browsing data cleared.")
    
    def _ad_blocker_settings(self) -> None:
        """Show ad blocker settings."""
        messagebox.showinfo("Ad Blocker", "Ad blocker settings not implemented yet.")
    
    def _show_about(self) -> None:
        """Show about dialog."""
        messagebox.showinfo(
            "About Wink Browser",
            "Wink Browser\n"
            "A modern privacy-focused web browser\n"
            "Version 0.1.0\n\n"
            "© 2023 Wink Browser Project"
        )
    
    def _close(self) -> None:
        """Close the browser window."""
        self.root.destroy() 