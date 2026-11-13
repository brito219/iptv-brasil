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
PROBE_TIMEOUT_S = 15
CONCURRENCY = 4
MINIMUM_CHANNELS = 100
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
JELLYFIN_CONTAINER = "homelab-jellyfin-1"
FFPROBE_PATH = "/usr/lib/jellyfin-ffmpeg/ffprobe"


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def read_file(path):
    with open(path, encoding="utf-8", errors="replace") as file:
        return file.read()


def extract_attribute(line, key):
    match = re.search(rf'{key}="([^"]*)"', line)
    return match.group(1) if match else ""


def parse_m3u(text):
    entries = []
    name = None
    group = ""
    tvg_id = ""
    tvg_logo = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            group = extract_attribute(line, "group-title")
            tvg_id = extract_attribute(line, "tvg-id")
            tvg_logo = extract_attribute(line, "tvg-logo")
            match = re.search(r",([^,]*)$", line)
            name = match.group(1).strip() if match else line
        elif line.startswith("http"):
            if name:
                entries.append({
                    "name": name,
                    "group": group,
                    "url": line,
                    "tvg_id": tvg_id,
                    "tvg_logo": tvg_logo,
                })
            name = None
            group = ""
            tvg_id = ""
            tvg_logo = ""
    return entries


def is_playable(url):
    command = [
        "docker", "exec", JELLYFIN_CONTAINER, FFPROBE_PATH,
        "-hide_banner", "-v", "error",
        "-timeout", str(PROBE_TIMEOUT_S * 1_000_000),
        "-i", url,
        "-show_entries", "format=format_name", "-of", "csv=p=0",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_S + 10,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


def test_streams(entries):
    working = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(is_playable, entry["url"]): entry for entry in entries}
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
        attributes = []
        if entry.get("tvg_id"):
            attributes.append(f'tvg-id="{entry["tvg_id"]}"')
        if entry.get("tvg_logo"):
            attributes.append(f'tvg-logo="{entry["tvg_logo"]}"')
        attributes.append(f'group-title="{entry["group"] or "Canais"}"')
        lines.append(f'#EXTINF:-1 {" ".join(attributes)},{entry["name"]}')
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
    if len(working) < MINIMUM_CHANNELS:
        print(f"aborting: only {len(working)} working channels (minimum {MINIMUM_CHANNELS})", file=sys.stderr)
        sys.exit(1)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        file.write(build_m3u(working))
    write_status(len(working), len(entries))
    print(f"working: {len(working)} / tested: {len(entries)}")


if __name__ == "__main__":
    main()
