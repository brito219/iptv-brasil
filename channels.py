import json
import urllib.request
import xml.etree.ElementTree as ET

GUIDES_URL = "https://iptv-org.github.io/api/guides.json"
OUTPUT_FILE = "channels.xml"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


def download_guides():
    request = urllib.request.Request(GUIDES_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def build_channels_xml(guides):
    root = ET.Element("channels")
    for guide in guides:
        channel = guide.get("channel") or ""
        feed = guide.get("feed") or ""
        site = guide.get("site") or ""
        site_id = guide.get("site_id") or ""
        site_name = guide.get("site_name") or ""
        lang = guide.get("lang") or "pt"
        xmltv_id = f"{channel}@{feed}"
        ET.SubElement(
            root,
            "channel",
            {
                "site": site,
                "lang": lang,
                "xmltv_id": xmltv_id,
                "site_id": site_id,
            },
        ).text = site_name or xmltv_id
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main():
    guides = [guide for guide in download_guides() if (guide.get("channel") or "").endswith(".br")]
    xml = build_channels_xml(guides)
    with open(OUTPUT_FILE, "wb") as file:
        file.write(xml)
    print(f"channels: {len(guides)}")


if __name__ == "__main__":
    main()
