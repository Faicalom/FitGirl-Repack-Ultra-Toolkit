# Smart Download Link Toolkit

A Windows command-line toolkit by **FaicalOm_DZ** for extracting page links, resolving direct links, organizing multi-part downloads, and sending selected files to Internet Download Manager (IDM).

## Features

- One-click workflow through `Run_Toolkit.bat`
- Headless browser extraction using Playwright
- Fast async direct-link resolving
- Smart sender for IDM
- Separates main archive parts from optional/addon groups
- Supports choosing all files, ranges, or specific parts
- Can add links to IDM queue or start the IDM queue automatically
- Auto-detects `IDMan.exe` from common install paths and Windows Registry

## Project files

```text
Page_Link_Extractor.py       # Stage 1: extracts source links from the page
Direct_Link_Resolver.py      # Stage 2: resolves source links into direct links
Download_Manager_Sender.py   # Stage 3: smart file selection and IDM sending
Run_Toolkit.bat              # One-click Windows launcher
requirements.txt             # Python dependencies
LICENSE                      # GPL-3.0-or-later license
NOTICE                       # Attribution notice
```

## Requirements

- Windows
- Python 3.10+
- Internet Download Manager installed
- Chromium for Playwright

Install dependencies:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Usage

1. Put all project files in one folder.
2. Double-click `Run_Toolkit.bat`.
3. Paste the source page URL.
4. Wait for extraction and resolving.
5. Select what to send to IDM:
   - all files
   - main parts
   - addon/optional groups
6. Choose whether to add to IDM queue or start downloading immediately.

## Generated files

The toolkit creates temporary files during a run. They are ignored by Git and can be cleaned by the sender:

```text
source_links.txt
source_manifest.txt
real_direct_links.txt
resolved_manifest.txt
resolved_map_debug.txt
failed_links.txt
```

## License and attribution

This project is open source under **GPL-3.0-or-later**.

You may fork, improve, and redistribute it, but you must keep the license and attribution to **FaicalOm_DZ**.

## Disclaimer

Use this toolkit only with files and links you are authorized to access and download. The author is not responsible for misuse.
