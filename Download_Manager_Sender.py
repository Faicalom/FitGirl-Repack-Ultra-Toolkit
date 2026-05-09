# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 FaicalOm_DZ
#
# Smart Download Link Toolkit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License v3.0 or later.

import os
import re
import subprocess
import time
import winreg
from datetime import datetime
from collections import defaultdict

def log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def find_idm_path():
    possible_paths = [
        r"C:\Program Files (x86)\Internet Download Manager\IDMan.exe",
        r"C:\Program Files\Internet Download Manager\IDMan.exe",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path

    registry_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Internet Download Manager"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Internet Download Manager"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Internet Download Manager"),
    ]
    for root, reg_path in registry_paths:
        try:
            with winreg.OpenKey(root, reg_path) as key:
                install_location, _ = winreg.QueryValueEx(key, "InstallLocation")
                idm_exe = os.path.join(install_location, "IDMan.exe")
                if os.path.exists(idm_exe):
                    return idm_exe
        except Exception:
            pass

    print("❌ IDM not found automatically.")
    custom_path = input("Paste full path to IDMan.exe: ").strip().strip('"')
    if custom_path and os.path.exists(custom_path):
        return custom_path
    return None

IDM_PATH = find_idm_path()
if not IDM_PATH:
    log("❌ IDM not found!")
    input("Press Enter to exit...")
    exit()

IDM_DELAY = 0.45

def extract_filename_from_source_url(source_url):
    if "#" in source_url:
        return source_url.split("#", 1)[1].strip()
    return os.path.basename(source_url) or "unknown"

def get_addon_group_name(filename):
    lower = filename.lower()
    if "setup" in lower or lower.endswith(".exe"):
        return filename
    name = re.sub(r'-\d+\.(bin|rar)$', '', filename, flags=re.I)
    name = re.sub(r'\.part\d+\.rar$', '', name, flags=re.I)
    name = re.sub(r'\.\w+$', '', name)
    return name.strip() if name else "other-addons"

def get_part_number(filename):
    """ترتيب MAIN PARTS حسب رقم part"""
    match = re.search(r'part0*(\d+)\.rar', filename, re.I)
    return int(match.group(1)) if match else 999999

if not os.path.exists("resolved_map_debug.txt"):
    log("❌ resolved_map_debug.txt not found!")
    input("Press Enter to exit...")
    exit()

log("✅ Reading resolved_map_debug.txt...")

files = []
with open("resolved_map_debug.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or '|' not in line:
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 4:
            continue
        try:
            idx = int(parts[0])
            source_part = parts[2]
            real_url = parts[3]
            filename = extract_filename_from_source_url(source_part)
            if not filename or filename.lower() == "unknown":
                filename = f"file_{idx:03d}"
            files.append({
                "index": idx,
                "filename": filename,
                "real_url": real_url
            })
        except:
            continue

def classify(filename):
    lower = filename.lower()
    if re.search(r'part\d+\.rar', lower) and not any(x in lower for x in ["optional", "selective", "bonus", "soundtrack", "fg-optional", "language", "voice", "dlc", "setup", ".exe", "bin"]):
        return "MAIN_PART"
    return "ADDON"

for f in files:
    f["category"] = classify(f["filename"])

main_parts = [f for f in files if f["category"] == "MAIN_PART"]
addon_files = [f for f in files if f["category"] == "ADDON"]

# ترتيب MAIN PARTS حسب رقم part
main_parts.sort(key=lambda f: get_part_number(f["filename"]))

addon_groups = defaultdict(list)
for f in addon_files:
    group = get_addon_group_name(f["filename"])
    addon_groups[group].append(f)

log(f"✅ Loaded {len(files)} files")
log(f"   MAIN PARTS : {len(main_parts)}")
log(f"   ADDON groups : {len(addon_groups)}")

def send_to_idm(links_to_send, mode="queue"):
    if mode == "queue":
        log(f"🚀 Adding {len(links_to_send)} links to IDM queue...")
        for link in links_to_send:
            try:
                subprocess.run([IDM_PATH, "/d", link, "/a"], check=True, shell=False)
                time.sleep(IDM_DELAY)
            except Exception as e:
                log(f"   ❌ Failed: {str(e)}")
        log("✅ Added to IDM queue successfully!")
    else:  # start mode
        log(f"🚀 Adding {len(links_to_send)} links to queue then starting download...")
        for link in links_to_send:
            try:
                subprocess.run([IDM_PATH, "/d", link, "/a"], check=True, shell=False)
                time.sleep(IDM_DELAY)
            except Exception as e:
                log(f"   ❌ Failed to add: {str(e)}")
        time.sleep(1)
        log("▶ Starting IDM queue...")
        for i in range(3):
            try:
                subprocess.run([IDM_PATH, "/s"], check=True, shell=False)
                time.sleep(1)
            except Exception as e:
                log(f"   ❌ Failed to start queue attempt {i+1}: {str(e)}")
        log("✅ IDM queue start command sent successfully!")

def clean_temp_files():
    temp = ["source_links.txt", "source_manifest.txt", "fuckingfast_links.txt", "fuckingfast_manifest.txt", "real_direct_links.txt",
            "resolved_manifest.txt", "resolved_map_debug.txt", "failed_links.txt",
            "selected_links.txt", "روابط_نهائية.txt"]
    for f in temp:
        if os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass
    log("✅ Temporary files cleaned")

def show_preview(selected):
    print(f"\nSelected files ({len(selected)}):")
    for i, f in enumerate(selected[:10], 1):
        print(f"   [{i}] {f['filename']}")
    if len(selected) > 10:
        print(f"   ... and {len(selected)-10} more")

while True:
    print("\n" + "="*75)
    print("          FaicalOm_DZ Smart Download Sender")
    print("="*75)
    print("1 - Send ALL files")
    print(f"2 - MAIN game parts only ({len(main_parts)})")
    print(f"3 - ADDONS / optional / bonus / setup / exe ({len(addon_groups)} groups)")
    print("0 - Cancel and exit")
    print("="*75)
    
    choice = input("\nEnter choice (0-3): ").strip()
    
    if choice == "0":
        log("❌ Cancelled")
        break
    
    selected = []
    
    if choice == "1":
        selected = files
    elif choice == "2":
        # MAIN sub-menu
        print("\nMAIN GAME PARTS")
        print(f"Total main parts: {len(main_parts)}")
        print("1 - Send ALL main parts")
        print("2 - Send RANGE of main parts")
        print("3 - Send SPECIFIC main parts")
        print("0 - Back")
        sub = input("Choice: ").strip()
        
        if sub == "1":
            selected = main_parts
        elif sub == "2":
            rng = input("From / To (e.g. 10/20 or 10و20): ").strip()
            try:
                fr, to = map(int, re.split(r'[,/;\sو]+', rng)[:2])
                fr, to = min(fr, to), max(fr, to)
                selected = [main_parts[i-1] for i in range(fr, to+1) if 1 <= i <= len(main_parts)]
            except:
                log("Invalid range")
                continue
        elif sub == "3":
            nums = input("Specific parts (e.g. 1/5/10 or 1و5و10): ").strip()
            nums_list = [int(x) for x in re.split(r'[,/;\sو]+', nums) if x.isdigit()]
            selected = [main_parts[n-1] for n in nums_list if 1 <= n <= len(main_parts)]
        else:
            continue
    elif choice == "3":
        print("\n" + "="*60)
        print("ADDONS / OPTIONAL GROUPS")
        print("="*60)
        groups_list = list(addon_groups.items())
        for i, (group_name, group_files) in enumerate(groups_list, 1):
            print(f"{i} - {group_name} ({len(group_files)} files)")
        print("0 - Back")
        print("="*60)
        
        g_choice = input("\nChoose group: ").strip()
        if g_choice == "0":
            continue
        try:
            g_idx = int(g_choice) - 1
            group_name, group_files = groups_list[g_idx]
        except:
            log("Invalid group")
            continue
        
        print(f"\n{group_name}")
        for i, f in enumerate(group_files, 1):
            print(f"   {i} - {f['filename']}")
        
        print("\n1 - Send ALL files in this group")
        print("2 - Send SPECIFIC files")
        print("0 - Back")
        sub = input("Choice: ").strip()
        
        if sub == "1":
            selected = group_files
        elif sub == "2":
            nums = input("Enter numbers (e.g. 1/3/5 or 1و3و5): ").strip()
            nums_list = [int(x) for x in re.split(r'[,/;\sو]+', nums) if x.isdigit()]
            selected = [group_files[n-1] for n in nums_list if 1 <= n <= len(group_files)]
        else:
            continue
    else:
        log("❌ Invalid choice")
        continue
    
    if not selected:
        log("❌ No files selected")
        continue
    
    show_preview(selected)
    confirm = input("\nSend to IDM? (Y/N): ").strip().upper()
    
    if confirm != "Y":
        log("❌ Cancelled")
        continue
    
    print("\n" + "="*50)
    print("IDM ACTION")
    print("="*50)
    print("1 - Add to IDM queue only")
    print("2 - Start downloading immediately")
    print("0 - Back")
    print("="*50)
    action = input("Choice: ").strip()
    
    if action == "0":
        continue
    elif action == "1":
        mode = "queue"
    elif action == "2":
        mode = "start"
    else:
        log("❌ Invalid action")
        continue
    
    send_to_idm([f["real_url"] for f in selected], mode)
    
    if input("\nClean temporary files? (Y/N): ").strip().upper() == "Y":
        clean_temp_files()
    log("🎉 Operation completed successfully!")
    break

input("\nPress Enter to exit...")