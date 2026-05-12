# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 FaicalOm_DZ
#
# FitGirl Repack Ultra Toolkit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License v3.0 or later.

from playwright.sync_api import sync_playwright, TimeoutError
import re
from urllib.parse import urljoin, unquote
from datetime import datetime
import time

# ================== VERSION SETTINGS ==================
HEADLESS = True
BLOCK_RESOURCES = True
DEBUG_LOGS = False

PAGE_TIMEOUT = 20000
SECTION_TIMEOUT = 12000
CLICK_TIMEOUT = 8000
LINKS_TIMEOUT = 8000


def log(message):
    if DEBUG_LOGS or any(marker in message for marker in ["[INFO]", "[OK]", "[WARN]", "[ERROR]"]):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")


def block_resources(route):
    """Block non-essential resources to speed up page loading."""
    if route.request.resource_type in ["image", "font", "stylesheet", "media"]:
        route.abort()
    else:
        route.continue_()


def extract_filename_from_url(url, index):
    """Return a readable file name from the URL fragment when available."""
    if "#" in url:
        name = url.split("#", 1)[1].strip()
        if name:
            return unquote(name)
    return f"file_{index:03d}"


# ================== MAIN EXECUTION ==================
source_page_url = input("Paste source page URL: ").strip()

start_time = time.perf_counter()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=HEADLESS)
    context = browser.new_context()

    if BLOCK_RESOURCES:
        context.route("**/*", block_resources)

    page = context.new_page()

    log("[OK] Browser started in headless mode")
    page.goto(source_page_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
    log(f"[OK] Page opened: {source_page_url}")

    # Wait for the Download Mirrors section.
    page.wait_for_selector("h3:has-text('Download Mirrors')", timeout=SECTION_TIMEOUT)
    log("[OK] Found Download Mirrors section")

    # ================== FIND THE FUCKINGFAST SECTION ==================
    log("[INFO] Looking for Filehoster: FuckingFast section...")

    try:
        fuckingfast_section = page.locator("text=Filehoster: FuckingFast").first
        if fuckingfast_section.count() == 0:
            raise Exception("Section not found")

        log("[OK] Found Filehoster: FuckingFast section")

        # Click the button inside this section only.
        click_selector = "text=Filehoster: FuckingFast >> .. >> text=Click to show direct links"
        page.click(click_selector, timeout=CLICK_TIMEOUT)
        log("[OK] Clicked 'Click to show direct links' inside the FuckingFast section")

    except Exception:
        log("[WARN] Primary selector failed, trying fallback...")
        try:
            section = page.locator("text=Filehoster: FuckingFast").first
            section.locator("..").get_by_text("Click to show direct links").click(timeout=CLICK_TIMEOUT)
            log("[OK] Clicked the button using fallback")
        except Exception as exc:
            log(f"[ERROR] Failed to click the FuckingFast button: {str(exc)[:100]}")
            log("   Make sure the section exists on the page")
            browser.close()
            raise SystemExit(1)

    # Wait for FuckingFast links to appear.
    page.wait_for_selector("a[href*='fuckingfast.co']", timeout=LINKS_TIMEOUT)
    log("[OK] Opened FuckingFast links")

    # ================== EXTRACT LINKS FROM THE CONTAINER ONLY ==================
    fuckingfast_container = page.locator("text=Filehoster: FuckingFast").locator(".. >> ..")

    # Collect href values from the container.
    all_hrefs = fuckingfast_container.locator("a[href]").evaluate_all(
        "(els) => els.map(a => a.href)"
    )

    fuckingfast_links = []
    for href in all_hrefs:
        if not href:
            continue
        full_url = urljoin(source_page_url, href.strip())
        if "fuckingfast.co" in full_url:
            fuckingfast_links.append(full_url)

    # Remove duplicates while preserving page order.
    unique_links = list(dict.fromkeys(fuckingfast_links))

    # ================== SAVE + REPORT ==================
    elapsed = time.perf_counter() - start_time

    if unique_links:
        # Canonical generic output files used by the toolkit.
        with open("source_links.txt", "w", encoding="utf-8") as file_obj:
            for link in unique_links:
                file_obj.write(link + "\n")

        with open("source_manifest.txt", "w", encoding="utf-8") as file_obj:
            for index, link in enumerate(unique_links, 1):
                filename = extract_filename_from_url(link, index)
                file_obj.write(f"{index}|{filename}|{link}\n")

        # Backward-compatible aliases for older local workflows.
        with open("fuckingfast_links.txt", "w", encoding="utf-8") as file_obj:
            for link in unique_links:
                file_obj.write(link + "\n")

        with open("fuckingfast_manifest.txt", "w", encoding="utf-8") as file_obj:
            for index, link in enumerate(unique_links, 1):
                filename = extract_filename_from_url(link, index)
                file_obj.write(f"{index}|{filename}|{link}\n")

        log(f"[OK] Extracted {len(unique_links)} source links successfully")
        log(f"   First link : {unique_links[0]}")
        log(f"   Last link  : {unique_links[-1]}")
        log(f"   Total time : {elapsed:.2f} seconds")
        log("   Saved: source_links.txt and source_manifest.txt")
    else:
        log("[ERROR] No FuckingFast links were found")
        log("   Saving the HTML page for debugging...")
        with open("debug_fitgirl_page.html", "w", encoding="utf-8") as file_obj:
            file_obj.write(page.content())
        log("   Saved debug_fitgirl_page.html")
        log("   Check that Filehoster: FuckingFast exists on the page")

    browser.close()
    log("[OK] Stage 1 finished successfully. You can now run Direct_Link_Resolver.py")
