# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 FaicalOm_DZ
#
# Smart Download Link Toolkit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License v3.0 or later.

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import os
import time
from datetime import datetime

# ================== إعدادات ==================
HEADLESS = True
CONCURRENCY = 4
CONCURRENCY_SAFE = 2
DEBUG_LOGS = False
DEBUG_SCREENSHOTS = False

MAX_RETRIES = 2
PAGE_TIMEOUT = 9000
BUTTON_TIMEOUT = 7000
POPUP_TIMEOUT = 2500
DOWNLOAD_TIMEOUT = 10000

SAFE_PAGE_TIMEOUT = 15000
SAFE_BUTTON_TIMEOUT = 12000
SAFE_POPUP_TIMEOUT = 6000
SAFE_DOWNLOAD_TIMEOUT = 20000

LINKS_FILE_CANDIDATES = ["source_links.txt", "fuckingfast_links.txt"]
MANIFEST_FILE_CANDIDATES = ["source_manifest.txt", "fuckingfast_manifest.txt"]

def first_existing(paths):
    for path in paths:
        if os.path.exists(path):
            return path
    return None

resolved_map = {}           # index -> real_url
file_lock = asyncio.Lock()
failed_first_pass = []      # list of (index, link, filename)
final_failed = []           # list of (index, link, filename)

def log(message):
    if DEBUG_LOGS or "OK" in message or "FAILED" in message or "انتهت" in message or "Retry" in message:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

async def block_resources(route):
    if route.request.resource_type in ["image", "font", "stylesheet", "media"]:
        await route.abort()
    else:
        await route.continue_()

def parse_manifest():
    """Read the source manifest flexibly when it exists."""
    manifest_file = first_existing(MANIFEST_FILE_CANDIDATES)
    if not manifest_file:
        return {}, {}
    
    index_to_filename = {}
    source_to_filename = {}
    
    with open(manifest_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or '|' not in line:
                continue
            parts = [p.strip() for p in line.split('|')]
            
            if len(parts) == 3:
                # index|filename|source OR index|source|filename OR source|filename|index
                p1, p2, p3 = parts
                # أول رقم = index
                if p1.isdigit():
                    idx = int(p1)
                    if 'http' in p3.lower():
                        filename = p2
                        source = p3
                    else:
                        filename = p3
                        source = p2
                elif p2.isdigit():
                    idx = int(p2)
                    filename = p1
                    source = p3
                else:
                    idx = int(p3)
                    filename = p1
                    source = p2
                index_to_filename[idx] = filename
                source_to_filename[source] = filename
                
            elif len(parts) == 2:
                p1, p2 = parts
                if 'http' in p1.lower():
                    source = p1
                    filename = p2
                else:
                    source = p2
                    filename = p1
                source_to_filename[source] = filename
                # إذا كان هناك index في مكان آخر، نتركه للـ fallback
    
    return index_to_filename, source_to_filename

async def process_single_link(context, link, index, filename, total, semaphore, safe_mode=False, fail_list=None):
    async with semaphore:
        log(f"[{index}/{total}] جاري معالجة...")
        
        for attempt in range(1, MAX_RETRIES + 1):
            is_safe = safe_mode or (attempt == 2)
            popup_to = SAFE_POPUP_TIMEOUT if is_safe else POPUP_TIMEOUT
            download_to = SAFE_DOWNLOAD_TIMEOUT if is_safe else DOWNLOAD_TIMEOUT
            
            captured_for_current = []
            request_event = asyncio.Event()
            
            def capture_direct_link(request):
                if "dl.fuckingfast.co/dl/" in request.url and request.url not in captured_for_current:
                    captured_for_current.append(request.url)
                    request_event.set()
            
            page = None
            try:
                page = await context.new_page()
                await page.route("**/*", block_resources)
                page.on("request", capture_direct_link)
                
                await page.goto(link, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT if not is_safe else SAFE_PAGE_TIMEOUT)
                
                download_btn = await page.wait_for_selector("text=DOWNLOAD", timeout=BUTTON_TIMEOUT if not is_safe else SAFE_BUTTON_TIMEOUT)
                
                try:
                    async with page.expect_popup(timeout=popup_to) as popup_info:
                        await download_btn.click()
                    popup = await popup_info.value
                    await popup.close()
                except PlaywrightTimeoutError:
                    pass
                
                await asyncio.sleep(0.5)
                
                download_btn = await page.wait_for_selector("text=DOWNLOAD", timeout=BUTTON_TIMEOUT if not is_safe else SAFE_BUTTON_TIMEOUT)
                
                real_url = None
                try:
                    async with page.expect_download(timeout=download_to) as download_info:
                        await download_btn.click()
                    download = await download_info.value
                    real_url = download.url
                    await download.cancel()
                except PlaywrightTimeoutError:
                    if captured_for_current:
                        real_url = captured_for_current[0]
                    else:
                        try:
                            await asyncio.wait_for(request_event.wait(), timeout=2.0)
                            real_url = captured_for_current[0]
                        except asyncio.TimeoutError:
                            pass
                
                if real_url:
                    async with file_lock:
                        resolved_map[index] = real_url
                    log(f"[{index}/{total}] OK")
                    await page.close()
                    return True
                
                log(f"[{index}/{total}] ⚠️ محاولة {attempt} فشلت")
                await page.close()
                
            except Exception:
                if page:
                    if DEBUG_SCREENSHOTS:
                        try:
                            await page.screenshot(path=f"debug_failed_{index:03d}_attempt_{attempt}.png")
                            with open(f"debug_failed_{index:03d}.html", "w", encoding="utf-8") as ff:
                                ff.write(await page.content())
                        except:
                            pass
                    await page.close()
                
                if attempt == MAX_RETRIES:
                    if fail_list is not None:
                        fail_list.append((index, link, filename))
                    log(f"[{index}/{total}] FAILED")
                    return False
                await asyncio.sleep(1)
        
        if fail_list is not None:
            fail_list.append((index, link, filename))
        log(f"[{index}/{total}] FAILED")
        return False

async def main():
    start_time = time.perf_counter()
    log(f"🚀 Direct Link Resolver - Concurrency: {CONCURRENCY}")
    
    open("real_direct_links.txt", "w", encoding="utf-8").close()
    open("resolved_manifest.txt", "w", encoding="utf-8").close()
    open("resolved_map_debug.txt", "w", encoding="utf-8").close()
    
    links_file = first_existing(LINKS_FILE_CANDIDATES)
    if not links_file:
        log("❌ No source links file found. Run Page_Link_Extractor.py first.")
        return
    
    # قراءة Manifest بطريقة مرنة
    index_to_filename, source_to_filename = parse_manifest()
    
    with open(links_file, "r", encoding="utf-8") as f:
        links = [line.strip() for line in f if line.strip()]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(accept_downloads=True)
        await context.route("**/*", block_resources)
        
        semaphore = asyncio.Semaphore(CONCURRENCY)
        tasks = []
        
        for idx, link in enumerate(links, 1):
            filename = index_to_filename.get(idx) or source_to_filename.get(link) or "unknown"
            task = process_single_link(context, link, idx, filename, len(links), semaphore, fail_list=failed_first_pass)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Retry للفاشلة
        if failed_first_pass:
            log(f"🔄 بدء Retry آمن لـ {len(failed_first_pass)} رابط فاشل...")
            safe_semaphore = asyncio.Semaphore(CONCURRENCY_SAFE)
            retry_tasks = []
            for idx, link, filename in failed_first_pass:
                task = process_single_link(context, link, idx, filename, len(links), safe_semaphore, safe_mode=True, fail_list=final_failed)
                retry_tasks.append(task)
            await asyncio.gather(*retry_tasks)
        
        # كتابة الملفات النهائية بالترتيب الأصلي
        with open("real_direct_links.txt", "w", encoding="utf-8") as f:
            for idx in range(1, len(links) + 1):
                if idx in resolved_map:
                    f.write(resolved_map[idx] + "\n")
        
        with open("resolved_manifest.txt", "w", encoding="utf-8") as f:
            for idx in range(1, len(links) + 1):
                if idx in resolved_map:
                    filename = index_to_filename.get(idx) or source_to_filename.get(links[idx-1]) or "unknown"
                    f.write(f"{idx}|{filename}|{resolved_map[idx]}\n")
        
        with open("resolved_map_debug.txt", "w", encoding="utf-8") as f:
            for idx in range(1, len(links) + 1):
                if idx in resolved_map:
                    filename = index_to_filename.get(idx) or source_to_filename.get(links[idx-1]) or "unknown"
                    f.write(f"{idx}|{filename}|{links[idx-1]}|{resolved_map[idx]}\n")
        
        if final_failed:
            with open("failed_links.txt", "w", encoding="utf-8") as f:
                for idx, link, filename in final_failed:
                    f.write(f"{idx}|{filename}|{link}\n")
            log(f"⚠️ تم حفظ {len(final_failed)} رابط فاشل نهائياً")
        else:
            open("failed_links.txt", "w", encoding="utf-8").close()
            log("✅ لا توجد روابط فاشلة نهائياً")
        
        elapsed = time.perf_counter() - start_time
        total = len(links)
        success = len(resolved_map)
        failed = len(final_failed)
        success_rate = (success / total * 100) if total else 0
        avg_time = elapsed / success if success else 0
        
        log(f"📊 تقرير الأداء النهائي:")
        log(f"   • إجمالي الروابط     : {total}")
        log(f"   • نجحت              : {success}")
        log(f"   • فشلت نهائياً      : {failed}")
        log(f"   • نسبة النجاح       : {success_rate:.1f}%")
        log(f"   • الزمن الكلي       : {elapsed:.1f} ثانية")
        log(f"✅ انتهت المرحلة 2 (v10/10) بنجاح! (real_direct_links.txt مرتب حسب الأصل)")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())