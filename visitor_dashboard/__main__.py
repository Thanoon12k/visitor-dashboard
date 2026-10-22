"""python -m visitor_dashboard geo-download <folder> [--country]
Downloads the free DB-IP Lite files, so places are found with no internet lookups (pass the folder as geo_dir)."""

import sys

from .geo import download


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] != "geo-download":
        print(__doc__)
        return 2
    for path in download(argv[1], city="--country" not in argv):
        print(f"saved {path} ({path.stat().st_size // 1_000_000} MB)")
    print("IP geolocation by DB-IP (https://db-ip.com), CC BY 4.0")
    return 0


sys.exit(main(sys.argv[1:]))
