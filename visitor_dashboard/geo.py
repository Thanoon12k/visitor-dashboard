"""Where a visitor is, from the IP address: country, region, city, internet provider and rough coordinates.

Two ways, tried in order:
  1. A local database file (DB-IP Lite, free, .mmdb): instant and works with no internet access. Download it with
     `python -m visitor_dashboard geo-download <folder>` and pass the folder as geo_dir. Needs `pip install maxminddb`.
  2. A free online service (ip-api.com, then ipwho.is), asked in batches and remembered per IP, so each address is
     looked up once. Called only after the visit is saved, never while the visitor waits.
"""

from __future__ import annotations

import ipaddress
import logging
from pathlib import Path

import requests

log = logging.getLogger("visitor_dashboard")
FIELDS = ("country_code", "country", "region", "city", "isp", "lat", "lon")
# Arabic names (the online services answer in English): countries by code, and Iraq's cities and governorates
AR_COUNTRIES = {
    "IQ": "العراق", "SA": "السعودية", "AE": "الإمارات", "KW": "الكويت", "QA": "قطر", "BH": "البحرين", "OM": "عُمان",
    "YE": "اليمن", "JO": "الأردن", "SY": "سوريا", "LB": "لبنان", "PS": "فلسطين", "EG": "مصر", "LY": "ليبيا", "TN": "تونس",
    "DZ": "الجزائر", "MA": "المغرب", "SD": "السودان", "MR": "موريتانيا", "SO": "الصومال", "TR": "تركيا", "IR": "إيران",
    "US": "أمريكا", "GB": "بريطانيا", "DE": "ألمانيا", "FR": "فرنسا", "NL": "هولندا", "SE": "السويد", "NO": "النرويج",
    "DK": "الدنمارك", "FI": "فنلندا", "BE": "بلجيكا", "CH": "سويسرا", "AT": "النمسا", "IT": "إيطاليا", "ES": "إسبانيا",
    "PT": "البرتغال", "GR": "اليونان", "PL": "بولندا", "RO": "رومانيا", "UA": "أوكرانيا", "RU": "روسيا", "IE": "إيرلندا",
    "LT": "ليتوانيا", "CZ": "التشيك", "HU": "هنغاريا", "BG": "بلغاريا", "CY": "قبرص", "CA": "كندا", "MX": "المكسيك",
    "BR": "البرازيل", "AU": "أستراليا", "NZ": "نيوزيلندا", "IN": "الهند", "PK": "باكستان", "BD": "بنغلاديش",
    "AF": "أفغانستان", "CN": "الصين", "JP": "اليابان", "KR": "كوريا الجنوبية", "SG": "سنغافورة", "MY": "ماليزيا",
    "ID": "إندونيسيا", "HK": "هونغ كونغ", "TW": "تايوان", "VN": "فيتنام", "TH": "تايلاند", "PH": "الفلبين",
    "AZ": "أذربيجان", "AM": "أرمينيا", "GE": "جورجيا", "KZ": "كازاخستان", "UZ": "أوزبكستان", "NG": "نيجيريا",
    "ZA": "جنوب أفريقيا", "KE": "كينيا", "ET": "إثيوبيا", "IL": "إسرائيل",
}
AR_CITIES = {
    "baghdad": "بغداد", "mosul": "الموصل", "erbil": "أربيل", "arbil": "أربيل", "basra": "البصرة", "basrah": "البصرة",
    "sulaymaniyah": "السليمانية", "as sulaymaniyah": "السليمانية", "kirkuk": "كركوك", "duhok": "دهوك", "dahuk": "دهوك",
    "najaf": "النجف", "an najaf": "النجف", "karbala": "كربلاء", "hillah": "الحلة", "al hillah": "الحلة", "babylon": "بابل",
    "nasiriyah": "الناصرية", "an nasiriyah": "الناصرية", "dhi qar": "ذي قار", "amarah": "العمارة", "al amarah": "العمارة",
    "maysan": "ميسان", "kut": "الكوت", "al kut": "الكوت", "wasit": "واسط", "diwaniyah": "الديوانية", "ad diwaniyah": "الديوانية",
    "al-qadisiyah": "القادسية", "samawah": "السماوة", "as samawah": "السماوة", "muthanna": "المثنى", "ramadi": "الرمادي",
    "ar ramadi": "الرمادي", "anbar": "الأنبار", "al anbar": "الأنبار", "fallujah": "الفلوجة", "baqubah": "بعقوبة",
    "diyala": "ديالى", "tikrit": "تكريت", "salah ad din": "صلاح الدين", "samarra": "سامراء", "nineveh": "نينوى",
    "ninawa": "نينوى", "zakho": "زاخو", "halabja": "حلبجة", "tal afar": "تلعفر", "kurdistan": "كردستان",
    "amman": "عمّان", "dubai": "دبي", "abu dhabi": "أبوظبي", "riyadh": "الرياض", "jeddah": "جدة", "kuwait city": "الكويت",
    "doha": "الدوحة", "cairo": "القاهرة", "beirut": "بيروت", "damascus": "دمشق", "istanbul": "إسطنبول", "ankara": "أنقرة",
    "tehran": "طهران", "london": "لندن", "berlin": "برلين", "paris": "باريس", "stockholm": "ستوكهولم",
}
LOCAL = {"country_code": "", "country": "", "region": "", "city": "شبكة محلية", "isp": "", "lat": None, "lon": None}


def is_public(ip: str) -> bool:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return address.is_global


def flag(code: str) -> str:
    """IQ -> 🇮🇶"""
    code = (code or "").upper()
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in code) if len(code) == 2 and code.isalpha() else ""


class Geo:
    def __init__(self, geo_dir: str | Path | None = None, online: bool = True, lang: str = "ar", timeout: float = 4):
        self.online, self.lang, self.timeout = online, lang, timeout
        self.city = self.asn = None
        if geo_dir:
            try:
                import maxminddb
            except ImportError:
                log.warning("visitor_dashboard: geo_dir is set but maxminddb is not installed (pip install maxminddb)")
            else:
                folder = Path(geo_dir).expanduser()
                for attr, patterns in (("city", ("*city*.mmdb", "*country*.mmdb")), ("asn", ("*asn*.mmdb",))):
                    found = [p for pattern in patterns for p in sorted(folder.glob(pattern))]
                    if found:
                        setattr(self, attr, maxminddb.open_database(str(found[0])))

    def arabic(self, place: dict) -> dict:
        if self.lang != "ar":
            return place
        for key in ("city", "region"):
            name = (place.get(key) or "").strip()
            plain = name.lower().replace(" governorate", "").replace(" province", "").replace("-", " ").replace("'", "")
            place[key] = AR_CITIES.get(plain, name)
        place["country"] = AR_COUNTRIES.get((place.get("country_code") or "").upper(), place.get("country") or "")
        return place

    @property
    def local(self) -> bool:
        return self.city is not None

    def name(self, names: dict) -> str:
        return (names or {}).get(self.lang) or (names or {}).get("en") or ""

    def from_file(self, ip: str) -> dict | None:
        if not self.city:
            return None
        try:
            found = self.city.get(ip) or {}
            asn = (self.asn.get(ip) or {}) if self.asn else {}
        except ValueError:
            return None
        if not found:
            return None
        where = found.get("location") or {}
        return {"country_code": (found.get("country") or {}).get("iso_code", ""),
                "country": self.name((found.get("country") or {}).get("names")),
                "region": self.name(((found.get("subdivisions") or [{}])[0]).get("names")),
                "city": self.name((found.get("city") or {}).get("names")),
                "isp": asn.get("autonomous_system_organization", ""),
                "lat": where.get("latitude"), "lon": where.get("longitude")}

    def quick(self, ip: str) -> dict | None:
        """The place when it needs no online lookup (a local address, or the database file has it)."""
        if not is_public(ip):
            return dict(LOCAL)
        place = self.from_file(ip)
        return self.arabic(place) if place else None

    def lookup(self, ips: list[str]) -> dict[str, dict]:
        """{ip: place} for the addresses that could be placed (private addresses get «شبكة محلية»)."""
        out, ask = {}, []
        for ip in dict.fromkeys(ips):
            if not is_public(ip):
                out[ip] = dict(LOCAL)
                continue
            place = self.from_file(ip)
            if place:
                out[ip] = place
            else:
                ask.append(ip)
        if ask and self.online:
            out.update(self.ask_online(ask))
        return {ip: self.arabic(place) for ip, place in out.items()}

    def ask_online(self, ips: list[str]) -> dict[str, dict]:
        out = {}
        try:  # ip-api.com: up to 100 addresses in one request, free for non-commercial use
            for start in range(0, len(ips), 100):
                response = requests.post(
                    "http://ip-api.com/batch?fields=status,query,countryCode,country,regionName,city,isp,org,lat,lon",
                    json=ips[start:start + 100], timeout=self.timeout)
                response.raise_for_status()
                for row in response.json():
                    if row.get("status") == "success":
                        out[row["query"]] = {"country_code": row.get("countryCode", ""), "country": row.get("country", ""),
                                             "region": row.get("regionName", ""), "city": row.get("city", ""),
                                             "isp": row.get("org") or row.get("isp", ""), "lat": row.get("lat"),
                                             "lon": row.get("lon")}
        except (requests.RequestException, ValueError) as exc:
            log.info("visitor_dashboard: ip-api.com failed (%s), trying ipwho.is", exc)
        for ip in [ip for ip in ips if ip not in out][:20]:
            try:
                row = requests.get(f"https://ipwho.is/{ip}", timeout=self.timeout).json()
            except (requests.RequestException, ValueError):
                break
            if row.get("success"):
                out[ip] = {"country_code": row.get("country_code", ""), "country": row.get("country", ""),
                           "region": row.get("region", ""), "city": row.get("city", ""),
                           "isp": (row.get("connection") or {}).get("org") or (row.get("connection") or {}).get("isp", ""),
                           "lat": row.get("latitude"), "lon": row.get("longitude")}
        return out


def download(folder: str | Path, city: bool = True) -> list[Path]:
    """Fetch this month's DB-IP Lite files (CC BY 4.0) into folder: the city file (~130 MB) and the provider file (~8 MB)."""
    import gzip
    from datetime import date, timedelta

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    saved = []
    for kind in (["city"] if city else ["country"]) + ["asn"]:
        for month in (date.today(), date.today().replace(day=1) - timedelta(days=1)):  # early in a month: last month's
            url = f"https://download.db-ip.com/free/dbip-{kind}-lite-{month:%Y-%m}.mmdb.gz"
            response = requests.get(url, stream=True, timeout=60)
            if response.ok:
                target = folder / f"dbip-{kind}-lite.mmdb"
                with gzip.GzipFile(fileobj=response.raw) as source, open(target, "wb") as out:
                    while chunk := source.read(1 << 20):
                        out.write(chunk)
                saved.append(target)
                break
    for old in folder.glob("dbip-country-lite.mmdb") if city else ():
        old.unlink()  # a city file makes the country one unnecessary
    return saved
