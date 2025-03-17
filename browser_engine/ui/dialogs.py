"""
Dialog windows for the browser UI.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import os
from typing import Dict, List, Optional, Any, Callable

from browser_engine.utils.config import Config
from browser_engine.privacy.ad_blocker import AdBlocker

logger = logging.getLogger(__name__)

class SettingsDialog:
    """Settings dialog for the browser."""
    
    def __init__(self, parent, config: Config, ad_blocker: AdBlocker):
        """
        Initialize the settings dialog.
        
        Args:
            parent: Parent window
            config: Configuration instance
            ad_blocker: Ad blocker instance
        """
        self.parent = parent
        self.config = config
        self.ad_blocker = ad_blocker
        
        # Create the dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)  # Make it a transient window
        self.dialog.grab_set()  # Make it modal
        
        # Initialize UI components
        self._init_ui()
        
        # Center the dialog on the parent window
        self._center_window()
        
        logger.debug("Settings dialog initialized")
    
    def _init_ui(self) -> None:
        """Initialize UI components."""
        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tab frames
        self.general_tab = ttk.Frame(self.notebook)
        self.privacy_tab = ttk.Frame(self.notebook)
        self.adblock_tab = ttk.Frame(self.notebook)
        self.advanced_tab = ttk.Frame(self.notebook)
        
        # Add tabs to the notebook
        self.notebook.add(self.general_tab, text="General")
        self.notebook.add(self.privacy_tab, text="Privacy")
        self.notebook.add(self.adblock_tab, text="Ad Blocker")
        self.notebook.add(self.advanced_tab, text="Advanced")
        
        # Fill tabs with content
        self._create_general_tab()
        self._create_privacy_tab()
        self._create_adblock_tab()
        self._create_advanced_tab()
        
        # Create bottom buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self._on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Apply", command=self._on_apply).pack(side=tk.RIGHT, padx=5)
    
    def _create_general_tab(self) -> None:
        """Create the general settings tab."""
        frame = ttk.Frame(self.general_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Home page setting
        ttk.Label(frame, text="Home page:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Get current home page from config
        home_page = self.config.get("browser.home_page", "https://www.example.com")
        
        self.home_page_var = tk.StringVar(value=home_page)
        ttk.Entry(frame, textvariable=self.home_page_var, width=50).grid(
            row=0, column=1, sticky=tk.W, pady=5, padx=5
        )
        
        # Default search engine
        ttk.Label(frame, text="Default search engine:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # Get current search engine from config
        search_engine = self.config.get("browser.search_engine", "Google")
        
        self.search_engine_var = tk.StringVar(value=search_engine)
        search_engines = ["Google", "Bing", "DuckDuckGo", "Yahoo"]
        ttk.Combobox(
            frame, 
            textvariable=self.search_engine_var,
            values=search_engines,
            state="readonly",
            width=20
        ).grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Download location
        ttk.Label(frame, text="Download location:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        # Get current download location from config
        download_dir = self.config.get("browser.download_dir", os.path.expanduser("~/Downloads"))
        
        self.download_dir_var = tk.StringVar(value=download_dir)
        download_frame = ttk.Frame(frame)
        download_frame.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        
        ttk.Entry(download_frame, textvariable=self.download_dir_var, width=40).pack(
            side=tk.LEFT, padx=0
        )
        ttk.Button(download_frame, text="Browse...", command=self._browse_download_dir).pack(
            side=tk.LEFT, padx=5
        )
        
        # Startup behavior
        ttk.Label(frame, text="On startup:").grid(row=3, column=0, sticky=tk.W, pady=5)
        
        # Get current startup behavior from config
        startup_behavior = self.config.get("browser.startup", "homepage")
        
        self.startup_var = tk.StringVar(value=startup_behavior)
        ttk.Radiobutton(
            frame, 
            text="Open the home page", 
            variable=self.startup_var,
            value="homepage"
        ).grid(row=3, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Radiobutton(
            frame, 
            text="Open the new tab page", 
            variable=self.startup_var,
            value="newtab"
        ).grid(row=4, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Radiobutton(
            frame, 
            text="Restore previous session", 
            variable=self.startup_var,
            value="restore"
        ).grid(row=5, column=1, sticky=tk.W, pady=2, padx=5)
    
    def _create_privacy_tab(self) -> None:
        """Create the privacy settings tab."""
        frame = ttk.Frame(self.privacy_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Cookie settings
        ttk.Label(frame, text="Cookie Settings", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=10
        )
        
        # Get current cookie settings from config
        cookie_policy = self.config.get("privacy.cookies", "accept_all")
        
        self.cookie_var = tk.StringVar(value=cookie_policy)
        ttk.Radiobutton(
            frame, 
            text="Accept all cookies", 
            variable=self.cookie_var,
            value="accept_all"
        ).grid(row=1, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        ttk.Radiobutton(
            frame, 
            text="Accept only from visited sites", 
            variable=self.cookie_var,
            value="accept_visited"
        ).grid(row=2, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        ttk.Radiobutton(
            frame, 
            text="Block all cookies", 
            variable=self.cookie_var,
            value="block_all"
        ).grid(row=3, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        # Tracking protection
        ttk.Label(frame, text="Tracking Protection", font=("Arial", 12, "bold")).grid(
            row=4, column=0, columnspan=2, sticky=tk.W, pady=(20, 10)
        )
        
        # Get current tracking settings from config
        do_not_track = self.config.get("privacy.do_not_track", True)
        block_trackers = self.config.get("privacy.block_trackers", True)
        
        self.do_not_track_var = tk.BooleanVar(value=do_not_track)
        ttk.Checkbutton(
            frame, 
            text="Send 'Do Not Track' with browsing requests", 
            variable=self.do_not_track_var
        ).grid(row=5, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        self.block_trackers_var = tk.BooleanVar(value=block_trackers)
        ttk.Checkbutton(
            frame, 
            text="Block known trackers", 
            variable=self.block_trackers_var
        ).grid(row=6, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        # History and cache
        ttk.Label(frame, text="History and Cache", font=("Arial", 12, "bold")).grid(
            row=7, column=0, columnspan=2, sticky=tk.W, pady=(20, 10)
        )
        
        # Get current history settings from config
        clear_history_on_exit = self.config.get("privacy.clear_history_on_exit", False)
        clear_cache_on_exit = self.config.get("privacy.clear_cache_on_exit", False)
        
        self.clear_history_var = tk.BooleanVar(value=clear_history_on_exit)
        ttk.Checkbutton(
            frame, 
            text="Clear history when browser closes", 
            variable=self.clear_history_var
        ).grid(row=8, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        self.clear_cache_var = tk.BooleanVar(value=clear_cache_on_exit)
        ttk.Checkbutton(
            frame, 
            text="Clear cache when browser closes", 
            variable=self.clear_cache_var
        ).grid(row=9, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        # Clear data buttons
        ttk.Button(
            frame, 
            text="Clear Browsing Data...", 
            command=self._show_clear_data_dialog
        ).grid(row=10, column=0, sticky=tk.W, pady=(20, 5), padx=5)
    
    def _create_adblock_tab(self) -> None:
        """Create the ad blocker settings tab."""
        frame = ttk.Frame(self.adblock_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Ad blocker enable/disable
        ttk.Label(frame, text="Ad Blocker Settings", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=10
        )
        
        # Get current ad blocker settings from config
        ad_blocker_enabled = self.config.get("adblock.enabled", True)
        
        self.ad_blocker_var = tk.BooleanVar(value=ad_blocker_enabled)
        ttk.Checkbutton(
            frame, 
            text="Enable ad blocker", 
            variable=self.ad_blocker_var
        ).grid(row=1, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        # Filter lists
        ttk.Label(frame, text="Filter Lists", font=("Arial", 12, "bold")).grid(
            row=2, column=0, columnspan=2, sticky=tk.W, pady=(20, 10)
        )
        
        # Get enabled filter lists from ad blocker
        enabled_lists = self.ad_blocker.get_enabled_lists()
        available_lists = self.ad_blocker.get_available_lists()
        
        # Create a frame with scrollable listbox for filter lists
        list_frame = ttk.Frame(frame)
        list_frame.grid(row=3, column=0, sticky=tk.NSEW, pady=5, padx=5, columnspan=2)
        
        frame.grid_rowconfigure(3, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.filter_listbox = tk.Listbox(
            list_frame, 
            selectmode=tk.MULTIPLE,
            yscrollcommand=scrollbar.set
        )
        self.filter_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.filter_listbox.yview)
        
        # Populate the listbox with available lists
        for list_name in available_lists:
            self.filter_listbox.insert(tk.END, list_name)
            if list_name in enabled_lists:
                self.filter_listbox.selection_set(available_lists.index(list_name))
        
        # Buttons for list management
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, sticky=tk.W, pady=5, padx=5, columnspan=2)
        
        ttk.Button(button_frame, text="Update Lists", command=self._update_filter_lists).pack(
            side=tk.LEFT, padx=5
        )
        
        ttk.Button(button_frame, text="Add Custom List", command=self._add_custom_list).pack(
            side=tk.LEFT, padx=5
        )
        
        ttk.Button(button_frame, text="Remove Selected", command=self._remove_selected_list).pack(
            side=tk.LEFT, padx=5
        )
        
        # Custom rules
        ttk.Label(frame, text="Custom Rules", font=("Arial", 12, "bold")).grid(
            row=5, column=0, columnspan=2, sticky=tk.W, pady=(20, 10)
        )
        
        # Create a text widget for custom rules
        custom_rules_frame = ttk.Frame(frame)
        custom_rules_frame.grid(row=6, column=0, sticky=tk.NSEW, pady=5, padx=5, columnspan=2)
        
        frame.grid_rowconfigure(6, weight=1)
        
        scrollbar = ttk.Scrollbar(custom_rules_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Get custom rules from ad blocker
        custom_rules = self.ad_blocker.get_custom_rules()
        
        self.custom_rules_text = tk.Text(
            custom_rules_frame, 
            height=5,
            yscrollcommand=scrollbar.set
        )
        self.custom_rules_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.custom_rules_text.insert(tk.END, '\n'.join(custom_rules))
        
        scrollbar.config(command=self.custom_rules_text.yview)
    
    def _create_advanced_tab(self) -> None:
        """Create the advanced settings tab."""
        frame = ttk.Frame(self.advanced_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # JavaScript settings
        ttk.Label(frame, text="JavaScript Settings", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=10
        )
        
        # Get current JavaScript settings from config
        javascript_enabled = self.config.get("advanced.javascript_enabled", True)
        javascript_strict = self.config.get("advanced.javascript_strict", False)
        
        self.javascript_var = tk.BooleanVar(value=javascript_enabled)
        ttk.Checkbutton(
            frame, 
            text="Enable JavaScript", 
            variable=self.javascript_var
        ).grid(row=1, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        self.javascript_strict_var = tk.BooleanVar(value=javascript_strict)
        ttk.Checkbutton(
            frame, 
            text="Strict JavaScript mode (may break some sites)", 
            variable=self.javascript_strict_var
        ).grid(row=2, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        # Network settings
        ttk.Label(frame, text="Network Settings", font=("Arial", 12, "bold")).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=(20, 10)
        )
        
        # Get current network settings from config
        cache_size = self.config.get("advanced.cache_size", 100)
        parallel_connections = self.config.get("advanced.parallel_connections", 8)
        timeout = self.config.get("advanced.timeout", 30)
        
        ttk.Label(frame, text="Cache size (MB):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.cache_size_var = tk.IntVar(value=cache_size)
        ttk.Spinbox(
            frame, 
            from_=10, 
            to=1000, 
            textvariable=self.cache_size_var,
            width=5
        ).grid(row=4, column=1, sticky=tk.W, pady=5, padx=5)
        
        ttk.Label(frame, text="Maximum parallel connections:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.parallel_var = tk.IntVar(value=parallel_connections)
        ttk.Spinbox(
            frame, 
            from_=1, 
            to=16, 
            textvariable=self.parallel_var,
            width=5
        ).grid(row=5, column=1, sticky=tk.W, pady=5, padx=5)
        
        ttk.Label(frame, text="Connection timeout (seconds):").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.timeout_var = tk.IntVar(value=timeout)
        ttk.Spinbox(
            frame, 
            from_=5, 
            to=120, 
            textvariable=self.timeout_var,
            width=5
        ).grid(row=6, column=1, sticky=tk.W, pady=5, padx=5)
        
        # User agent
        ttk.Label(frame, text="User Agent:", font=("Arial", 12, "bold")).grid(
            row=7, column=0, columnspan=2, sticky=tk.W, pady=(20, 10)
        )
        
        # Get current user agent from config
        user_agent = self.config.get("advanced.user_agent", "default")
        
        self.user_agent_var = tk.StringVar(value=user_agent)
        ttk.Radiobutton(
            frame, 
            text="Default", 
            variable=self.user_agent_var,
            value="default"
        ).grid(row=8, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        ttk.Radiobutton(
            frame, 
            text="Desktop (Chrome)", 
            variable=self.user_agent_var,
            value="chrome"
        ).grid(row=9, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        ttk.Radiobutton(
            frame, 
            text="Desktop (Firefox)", 
            variable=self.user_agent_var,
            value="firefox"
        ).grid(row=10, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        ttk.Radiobutton(
            frame, 
            text="Mobile (Android)", 
            variable=self.user_agent_var,
            value="android"
        ).grid(row=11, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        ttk.Radiobutton(
            frame, 
            text="Mobile (iPhone)", 
            variable=self.user_agent_var,
            value="iphone"
        ).grid(row=12, column=0, sticky=tk.W, pady=2, padx=5, columnspan=2)
        
        ttk.Radiobutton(
            frame, 
            text="Custom:", 
            variable=self.user_agent_var,
            value="custom"
        ).grid(row=13, column=0, sticky=tk.W, pady=2, padx=5)
        
        # Get custom user agent from config
        custom_user_agent = self.config.get("advanced.custom_user_agent", "")
        
        self.custom_ua_var = tk.StringVar(value=custom_user_agent)
        ttk.Entry(frame, textvariable=self.custom_ua_var, width=40).grid(
            row=13, column=1, sticky=tk.W, pady=2, padx=5
        )
    
    def _browse_download_dir(self) -> None:
        """Browse for download directory."""
        directory = filedialog.askdirectory(
            initialdir=self.download_dir_var.get(),
            title="Select Download Directory"
        )
        if directory:
            self.download_dir_var.set(directory)
    
    def _show_clear_data_dialog(self) -> None:
        """Show the clear browsing data dialog."""
        # In a real implementation, we would create a dialog to select what data to clear
        messagebox.showinfo("Clear Data", "Clear browsing data dialog would be shown here.")
    
    def _update_filter_lists(self) -> None:
        """Update ad blocker filter lists."""
        # In a real implementation, we would update the filter lists
        messagebox.showinfo("Update Lists", "Filter lists would be updated here.")
    
    def _add_custom_list(self) -> None:
        """Add a custom filter list."""
        # In a real implementation, we would show a dialog to add a custom list
        messagebox.showinfo("Add List", "Dialog to add a custom list would be shown here.")
    
    def _remove_selected_list(self) -> None:
        """Remove the selected filter list."""
        # In a real implementation, we would remove the selected list
        selected = self.filter_listbox.curselection()
        if selected:
            for i in selected:
                self.filter_listbox.delete(i)
    
    def _center_window(self) -> None:
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        
        # Get parent and dialog dimensions
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()
        px = self.parent.winfo_x()
        py = self.parent.winfo_y()
        
        dw = self.dialog.winfo_width()
        dh = self.dialog.winfo_height()
        
        # Calculate position
        x = px + (pw - dw) // 2
        y = py + (ph - dh) // 2
        
        # Set position
        self.dialog.geometry(f"+{x}+{y}")
    
    def _on_ok(self) -> None:
        """Handle OK button click."""
        # Apply settings
        self._apply_settings()
        
        # Close dialog
        self.dialog.destroy()
    
    def _on_cancel(self) -> None:
        """Handle Cancel button click."""
        # Close dialog without applying settings
        self.dialog.destroy()
    
    def _on_apply(self) -> None:
        """Handle Apply button click."""
        # Apply settings
        self._apply_settings()
    
    def _apply_settings(self) -> None:
        """Apply settings from the dialog to the config."""
        try:
            # General settings
            self.config.set("browser.home_page", self.home_page_var.get())
            self.config.set("browser.search_engine", self.search_engine_var.get())
            self.config.set("browser.download_dir", self.download_dir_var.get())
            self.config.set("browser.startup", self.startup_var.get())
            
            # Privacy settings
            self.config.set("privacy.cookies", self.cookie_var.get())
            self.config.set("privacy.do_not_track", self.do_not_track_var.get())
            self.config.set("privacy.block_trackers", self.block_trackers_var.get())
            self.config.set("privacy.clear_history_on_exit", self.clear_history_var.get())
            self.config.set("privacy.clear_cache_on_exit", self.clear_cache_var.get())
            
            # Ad blocker settings
            self.config.set("adblock.enabled", self.ad_blocker_var.get())
            
            # Get selected filter lists
            selected_indices = self.filter_listbox.curselection()
            selected_lists = [self.filter_listbox.get(i) for i in selected_indices]
            self.ad_blocker.set_enabled_lists(selected_lists)
            
            # Update custom rules
            custom_rules = self.custom_rules_text.get(1.0, tk.END).strip().split('\n')
            custom_rules = [rule for rule in custom_rules if rule.strip()]
            self.ad_blocker.set_custom_rules(custom_rules)
            
            # Advanced settings
            self.config.set("advanced.javascript_enabled", self.javascript_var.get())
            self.config.set("advanced.javascript_strict", self.javascript_strict_var.get())
            self.config.set("advanced.cache_size", self.cache_size_var.get())
            self.config.set("advanced.parallel_connections", self.parallel_var.get())
            self.config.set("advanced.timeout", self.timeout_var.get())
            self.config.set("advanced.user_agent", self.user_agent_var.get())
            
            if self.user_agent_var.get() == "custom":
                self.config.set("advanced.custom_user_agent", self.custom_ua_var.get())
            
            # Save the configuration
            self.config.save()
            
            logger.info("Settings applied")
            
        except Exception as e:
            logger.error(f"Error applying settings: {e}")
            messagebox.showerror("Error", f"Error applying settings: {e}")


class ClearDataDialog:
    """Dialog for clearing browsing data."""
    
    def __init__(self, parent):
        """
        Initialize the clear data dialog.
        
        Args:
            parent: Parent window
        """
        self.parent = parent
        
        # Create the dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Clear Browsing Data")
        self.dialog.geometry("400x350")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)  # Make it a transient window
        self.dialog.grab_set()  # Make it modal
        
        # Initialize UI components
        self._init_ui()
        
        # Center the dialog on the parent window
        self._center_window()
        
        logger.debug("Clear data dialog initialized")
    
    def _init_ui(self) -> None:
        """Initialize UI components."""
        frame = ttk.Frame(self.dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Clear the following items:", font=("Arial", 12, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 10)
        )
        
        # Time range selection
        ttk.Label(frame, text="Time range:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.time_range_var = tk.StringVar(value="last_hour")
        time_combo = ttk.Combobox(
            frame, 
            textvariable=self.time_range_var,
            values=["last_hour", "last_day", "last_week", "last_month", "all_time"],
            state="readonly",
            width=15
        )
        time_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Data checkboxes
        self.browsing_history_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame, 
            text="Browsing history", 
            variable=self.browsing_history_var
        ).grid(row=2, column=0, sticky=tk.W, pady=5, columnspan=2)
        
        self.cookies_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame, 
            text="Cookies and site data", 
            variable=self.cookies_var
        ).grid(row=3, column=0, sticky=tk.W, pady=5, columnspan=2)
        
        self.cache_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame, 
            text="Cached images and files", 
            variable=self.cache_var
        ).grid(row=4, column=0, sticky=tk.W, pady=5, columnspan=2)
        
        self.passwords_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, 
            text="Saved passwords", 
            variable=self.passwords_var
        ).grid(row=5, column=0, sticky=tk.W, pady=5, columnspan=2)
        
        self.form_data_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, 
            text="Autofill form data", 
            variable=self.form_data_var
        ).grid(row=6, column=0, sticky=tk.W, pady=5, columnspan=2)
        
        self.site_settings_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, 
            text="Site settings", 
            variable=self.site_settings_var
        ).grid(row=7, column=0, sticky=tk.W, pady=5, columnspan=2)
        
        self.hosted_data_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, 
            text="Hosted app data", 
            variable=self.hosted_data_var
        ).grid(row=8, column=0, sticky=tk.W, pady=5, columnspan=2)
        
        # Warning
        ttk.Label(
            frame, 
            text="Warning: This will delete the selected browsing data from your device.",
            wraplength=380,
            foreground="red"
        ).grid(row=9, column=0, sticky=tk.W, pady=(20, 10), columnspan=2)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=10, column=0, columnspan=2, pady=(10, 0), sticky=tk.E)
        
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(
            side=tk.LEFT, padx=5
        )
        
        ttk.Button(button_frame, text="Clear Data", command=self._clear_data).pack(
            side=tk.LEFT, padx=5
        )
    
    def _center_window(self) -> None:
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        
        # Get parent and dialog dimensions
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()
        px = self.parent.winfo_x()
        py = self.parent.winfo_y()
        
        dw = self.dialog.winfo_width()
        dh = self.dialog.winfo_height()
        
        # Calculate position
        x = px + (pw - dw) // 2
        y = py + (ph - dh) // 2
        
        # Set position
        self.dialog.geometry(f"+{x}+{y}")
    
    def _clear_data(self) -> None:
        """Clear the selected browsing data."""
        # In a real implementation, we would clear the selected data
        messagebox.showinfo("Clear Data", "Selected browsing data would be cleared here.")
        self.dialog.destroy() 