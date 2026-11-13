import json
import re
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

SOURCE_URLS = [
    "https://iptv-org.github.io/iptv/countries/br.m3u",
    "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plutotv_br.m3u",
]
PINNED_FILE = "essenciais.m3u"
OUTPUT_FILE = "brasil.m3u"
STATUS_FILE = "status.json"
REQUEST_TIMEOUT_S = 8
CONCURRENCY = 24
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def read_file(path):
    with open(path, encoding="utf-8", errors="replace") as file:
        return file.read()


def parse_m3u(text):
    entries = []
    name = None
    group = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            match = re.search(r'group-title="([^"]*)"', line)
            group = match.group(1) if match else ""
            match = re.search(r",([^,]*)$", line)
            name = match.group(1).strip() if match else line
        elif line.startswith("http"):
            if name:
                entries.append({"name": name, "group": group, "url": line})
            name = None
            group = ""
    return entries


def is_working(url):
    try:
        result = subprocess.run(
            [
                "curl", "-sk", "-m", str(REQUEST_TIMEOUT_S), "-L", "-r", "0-65535",
                "-o", "/dev/null", "-w", "%{http_code} %{size_download}", url,
            ],
            capture_output=True,
            text=True,
            timeout=REQUEST_TIMEOUT_S + 2,
        )
        parts = result.stdout.strip().split()
        code = parts[0] if parts else "ERR"
        size = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        return code.startswith("2") and size > 0
    except Exception:
        return False


def test_streams(entries):
    working = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(is_working, entry["url"]): entry for entry in entries}
        for future in as_completed(futures):
            if future.result():
                working.append(futures[future])
    return working


def dedupe(entries):
    seen_urls = set()
    result = []
    for entry in entries:
        if entry["url"] in seen_urls:
            continue
        seen_urls.add(entry["url"])
        result.append(entry)
    return result


def build_m3u(entries):
    entries = sorted(entries, key=lambda entry: (entry["group"].lower(), entry["name"].lower()))
    lines = ["#EXTM3U"]
    for entry in entries:
        group = entry["group"] or "Canais"
        lines.append(f'#EXTINF:-1 group-title="{group}",{entry["name"]}')
        lines.append(entry["url"])
    return "\n".join(lines) + "\n"


def write_status(working_count, tested_count):
    status = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "channels": working_count,
        "tested": tested_count,
    }
    with open(STATUS_FILE, "w", encoding="utf-8") as file:
        json.dump(status, file, ensure_ascii=False, indent=2)


def main():
    entries = []
    for url in SOURCE_URLS:
        try:
            entries += parse_m3u(download(url))
        except Exception as error:
            print(f"failed to download {url}: {error}", file=sys.stderr)
    entries += parse_m3u(read_file(PINNED_FILE))
    entries = dedupe(entries)
    working = test_streams(entries)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        file.write(build_m3u(working))
    write_status(len(working), len(entries))
    print(f"working: {len(working)} / tested: {len(entries)}")


if __name__ == "__main__":
    main()
