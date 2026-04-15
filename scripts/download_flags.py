"""Download flag images for the language picker.

Uses flagcdn.com which provides free flag PNGs.
Run this once to populate openwhisper/resources/flags/
"""
import urllib.request
from pathlib import Path

# Country codes we need (mapped from language codes)
COUNTRIES = [
    "us", "es", "fr", "de", "it", "br", "nl", "pl", "ru", "ua",
    "jp", "kr", "cn", "sa", "cz", "dk", "gr", "fi", "il", "in",
    "hu", "id", "my", "no", "ro", "sk", "se", "th", "tr", "vn",
    "za", "az", "by", "bg", "bd", "ba", "gb", "ee", "ir", "hr",
    "am", "is", "ge", "kz", "lt", "lv", "mk", "mn", "mt", "np",
    "lk", "si", "al", "rs", "ke", "ph", "pk",
]

FLAGS_DIR = Path(__file__).parent.parent / "openwhisper" / "resources" / "flags"


def download_flags():
    FLAGS_DIR.mkdir(parents=True, exist_ok=True)

    for code in COUNTRIES:
        url = f"https://flagcdn.com/24x18/{code}.png"
        dest = FLAGS_DIR / f"{code}.png"

        if dest.exists():
            print(f"  {code}.png already exists, skipping")
            continue

        try:
            print(f"  Downloading {code}.png...")
            urllib.request.urlretrieve(url, dest)
        except Exception as e:
            print(f"  Failed to download {code}: {e}")

    print(f"\nDone! Flags saved to {FLAGS_DIR}")


if __name__ == "__main__":
    print("Downloading flag images...\n")
    download_flags()
