# 😉 Wink Browser

A modern, privacy-focused web browser built in Python.

## Features

- **Privacy First**: Built-in ad and tracker blocking
- **Modern UI**: Clean, intuitive interface built with Python and Tkinter
- **Customizable**: Extensive settings to tailor your browsing experience
- **Lightweight**: Efficient resource usage compared to mainstream browsers
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Extension Support**: Support for securely sandboxed browser extensions
- **Brand New Browser Engine**: Not anu existing browser engine of any kind.
- **Freedom from big tech**: No influence from big tech.

## Components

- **HTML Parser**: Efficient HTML parsing using BeautifulSoup and html5lib
- **CSS Parser**: CSS parsing and styling with cssutils (WIP)
- **JavaScript Engine**: JavaScript execution via dukpy (embedded JavaScript interpreter)
- **Network Manager**: Handles HTTP requests, cookies, and caching
- **Ad Blocker**: Blocks ads and trackers using filter lists
- **Download Manager**: Manages file downloads with pause/resume support
- **History Manager**: Tracks and manages browsing history
- **Bookmark Manager**: Organizes and stores bookmarks
- **Extensions System**: Secure, sandboxed browser extensions

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/sneed-group/wink-browser.git
   cd wink-browser
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the browser:
   ```
   python main.py
   ```

## Usage

Wink Browser supports several command-line options:

- **Regular Mode**: `python main.py [url]`
- **Text-Only Mode**: `python main.py --text-only [url]` (Disables JavaScript for faster, lighter browsing)
- **Private Mode**: `python main.py --private [url]` (No history or cookies saved)
- **Debug Mode**: `python main.py --debug [url]` (Shows detailed debug information)

You can combine these options. For example, to run in both private and text-only mode:
```
python main.py --private --text-only https://example.com
```

### Known Issues and Workarounds

- **SSL Certificate Errors**: If you encounter SSL certificate verification errors, the browser will automatically retry without verification as a fallback. This is not recommended for security-sensitive browsing.
  
- **JavaScript Engine Issues**: The JavaScript engine may occasionally encounter event loop errors. If this happens, try using text-only mode (`--text-only` flag) which disables JavaScript execution.

## Configuration

Wink Browser stores its configuration in `~/.wink_browser/config.json`. This includes:

- General settings (homepage, search engine, etc.)
- Privacy settings (cookie policy, tracking protection)
- Ad blocker settings (filter lists, custom rules)
- Advanced settings (JavaScript, cache size, etc.)
- Extension settings and permissions

## Extensions

Wink Browser supports extensions that can enhance your browsing experience:

### Extension Structure

Extensions are stored in `~/.wink_browser/extensions/` with each extension in its own folder. An extension consists of:

- `extprops.csv`: Defines extension metadata and event handlers
- JavaScript files that handle different browser events

Example `extprops.csv`:
```csv
Key,Value
@name,My Extension
@version,1.0.0
@description,An example extension
@enabled,true

Script,Events
main.js,page_load,dom_ready
link_handler.js,link_click
```

### Extension Security

Extensions run in a secure sandbox with:

- JavaScript code filtering to block potentially harmful patterns
- Limited API access based on permissions
- Event-based architecture to minimize resource usage
- Isolation from the main browser context

### Creating Extensions

To create example extensions, run:
```
python -m browser_engine.extensions.setup_extensions
```

## Development

### Project Structure

```
wink-browser/
├── browser_engine/          # Core browser engine
│   ├── parser/              # HTML, CSS, and JS parsers
│   ├── privacy/             # Privacy features (ad blocker, etc.)
│   ├── media/               # Media handling (images, video, audio)
│   ├── extensions/          # Extension system
│   ├── ui/                  # User interface components
│   └── utils/               # Utility modules
├── main.py                  # Entry point
└── requirements.txt         # Dependencies
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the Sammy Public License - see the LICENSE file for details.

## Acknowledgments

- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing
- [cssutils](https://pypi.org/project/cssutils/) for CSS parsing
- [js2py](https://github.com/vlasovskikh/js2py) for JavaScript execution
- [Requests](https://requests.readthedocs.io/) for HTTP handling
- [Tkinter](https://docs.python.org/3/library/tkinter.html) for the UI 
