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

# ================== إعدادات النسخة 10/10 ==================
HEADLESS = True
BLOCK_RESOURCES = True
DEBUG_LOGS = False

PAGE_TIMEOUT = 20000
SECTION_TIMEOUT = 12000
CLICK_TIMEOUT = 8000
LINKS_TIMEOUT = 8000

def log(message):
    if DEBUG_LOGS or any(k in message for k in ["تم فتح", "تم العثور", "تم استخراج", "انتهت", "❌", "✅"]):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

def block_resources(route):
    """حظر الموارد غير المهمة لتسريع التحميل"""
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

# ================== التشغيل الرئيسي ==================
source_page_url = input("Paste source page URL: ").strip()

start_time = time.perf_counter()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=HEADLESS)
    context = browser.new_context()
    
    if BLOCK_RESOURCES:
        context.route("**/*", block_resources)
    
    page = context.new_page()
    
    log("✓ تم تشغيل المتصفح في الخلفية (headless)")
    page.goto(source_page_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
    log(f"✓ Page opened: {source_page_url}")
    
    # انتظار قسم Download Mirrors
    page.wait_for_selector("h3:has-text('Download Mirrors')", timeout=SECTION_TIMEOUT)
    log("✓ تم العثور على قسم Download Mirrors")
    
    # ================== البحث عن قسم FuckingFast ==================
    log("🔍 جاري البحث عن قسم Filehoster: FuckingFast...")
    
    try:
        fuckingfast_section = page.locator("text=Filehoster: FuckingFast").first
        if fuckingfast_section.count() == 0:
            raise Exception("لم يتم العثور على القسم")
        
        log("✓ تم العثور على قسم Filehoster: FuckingFast")
        
        # ضغط الزر داخل القسم فقط
        click_selector = "text=Filehoster: FuckingFast >> .. >> text=Click to show direct links"
        page.click(click_selector, timeout=CLICK_TIMEOUT)
        log("✓ تم الضغط على زر 'Click to show direct links' داخل قسم FuckingFast فقط")
        
    except Exception:
        log("⚠️ الـ selector الأول فشل → جاري الـ fallback")
        try:
            section = page.locator("text=Filehoster: FuckingFast").first
            section.locator("..").get_by_text("Click to show direct links").click(timeout=CLICK_TIMEOUT)
            log("✓ تم الضغط على الزر باستخدام الـ fallback")
        except Exception as e:
            log(f"❌ فشل في الضغط على زر FuckingFast: {str(e)[:100]}")
            log("   تأكد أن القسم موجود في الصفحة")
            browser.close()
            exit()
    
    # انتظار ذكي لظهور روابط FuckingFast
    page.wait_for_selector("a[href*='fuckingfast.co']", timeout=LINKS_TIMEOUT)
    log("✓ تم فتح روابط قسم FuckingFast")
    
    # ================== استخراج كل الروابط داخل صندوق FuckingFast فقط ==================
    fuckingfast_container = page.locator("text=Filehoster: FuckingFast").locator(".. >> ..")
    
    # الطريقة الصحيحة لـ Locator
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
    
    # منع التكرار مع الحفاظ على ترتيب الظهور في الصفحة
    unique_links = list(dict.fromkeys(fuckingfast_links))
    
    # ================== حفظ + تقرير ==================
    elapsed = time.perf_counter() - start_time
    
    if unique_links:
        # Canonical generic output files used by the toolkit
        with open("source_links.txt", "w", encoding="utf-8") as f:
            for link in unique_links:
                f.write(link + "\n")

        with open("source_manifest.txt", "w", encoding="utf-8") as f:
            for i, link in enumerate(unique_links, 1):
                filename = extract_filename_from_url(link, i)
                f.write(f"{i}|{filename}|{link}\n")

        # Backward-compatible aliases for older local workflows
        with open("fuckingfast_links.txt", "w", encoding="utf-8") as f:
            for link in unique_links:
                f.write(link + "\n")

        with open("fuckingfast_manifest.txt", "w", encoding="utf-8") as f:
            for i, link in enumerate(unique_links, 1):
                filename = extract_filename_from_url(link, i)
                f.write(f"{i}|{filename}|{link}\n")
        
        log(f"✅ Extracted {len(unique_links)} source links successfully")
        log(f"   First link : {unique_links[0]}")
        log(f"   Last link  : {unique_links[-1]}")
        log(f"   Total time : {elapsed:.2f} seconds")
        log("   Saved: source_links.txt and source_manifest.txt")
    else:
        log("❌ لم يتم العثور على أي روابط FuckingFast")
        log("   جاري حفظ صفحة HTML للتصحيح...")
        with open("debug_fitgirl_page.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        log("   تم حفظ debug_fitgirl_page.html")
        log("   تحقق من أن قسم Filehoster: FuckingFast موجود")
    
    browser.close()
    log("🎉 Stage 1 finished successfully. You can now run Direct_Link_Resolver.py")