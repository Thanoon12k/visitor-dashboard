"""The words the server shows, in English (the default) and Arabic.

Visits are saved in one language-neutral form (English place names from the lookup, "direct" / "internal"
origins, "Local network"), and put into the reader's language only when shown.
"""

from __future__ import annotations

import re

LANGS = ("en", "ar")
TEXT = {
    "en": {
        "title": "Site visitors", "password": "Password", "login": "Log in", "not_me": "Don't count my visits from this device",
        "wrong": "Wrong password.", "too_many": "Too many tries. Try again in 15 minutes.",
        "locked": "The dashboard is locked: no password is set in the site's settings.", "not_found": "This page doesn't exist.",
        "new_visitor": "New visitor", "visit": "Visit", "on": "on", "unknown_place": "Unknown place", "from": "From",
        "inside": "in {app}", "details": "All the details",
        "now": "just now", "minutes": "{n} min ago", "hours": "{n} h ago", "days": "{n} d ago",
        "mobile": "Mobile", "desktop": "Desktop", "tablet": "Tablet", "bot": "Bot",
        "direct": "Direct", "internal": "Internal", "local": "Local network",
    },
    "ar": {
        "title": "زوّار الموقع", "password": "الرمز السري", "login": "دخول", "not_me": "لا تحسب زياراتي من هذا الجهاز",
        "wrong": "الرمز غلط.", "too_many": "محاولات كثيرة. جرّب بعد ربع ساعة.",
        "locked": "اللوحة مقفولة: ما انحط رمز سري (password) بإعدادات الموقع.", "not_found": "هالصفحة مو موجودة.",
        "new_visitor": "زائر جديد", "visit": "زيارة", "on": "على", "unknown_place": "مكان غير معروف", "from": "جاي من",
        "inside": "داخل {app}", "details": "كل التفاصيل",
        "now": "هسه", "minutes": "قبل {n} دقيقة", "hours": "قبل {n} ساعة", "days": "قبل {n} يوم",
        "mobile": "موبايل", "desktop": "كمبيوتر", "tablet": "تابلت", "bot": "بوت",
        "direct": "مباشر", "internal": "داخلي", "local": "شبكة محلية",
    },
}
# saved by earlier versions in Arabic -> the neutral form
OLD = {"مباشر": "direct", "داخلي": "internal", "شبكة محلية": "local", "Local network": "local"}
ARABIC = re.compile(r"[؀-ۿ]")

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
    "al qadisiyah": "القادسية", "samawah": "السماوة", "as samawah": "السماوة", "muthanna": "المثنى", "ramadi": "الرمادي",
    "ar ramadi": "الرمادي", "anbar": "الأنبار", "al anbar": "الأنبار", "fallujah": "الفلوجة", "baqubah": "بعقوبة",
    "diyala": "ديالى", "tikrit": "تكريت", "salah ad din": "صلاح الدين", "samarra": "سامراء", "nineveh": "نينوى",
    "ninawa": "نينوى", "zakho": "زاخو", "halabja": "حلبجة", "tal afar": "تلعفر", "kurdistan": "كردستان",
    "amman": "عمّان", "dubai": "دبي", "abu dhabi": "أبوظبي", "riyadh": "الرياض", "jeddah": "جدة", "kuwait city": "الكويت",
    "doha": "الدوحة", "cairo": "القاهرة", "beirut": "بيروت", "damascus": "دمشق", "istanbul": "إسطنبول", "ankara": "أنقرة",
    "tehran": "طهران", "london": "لندن", "berlin": "برلين", "paris": "باريس", "stockholm": "ستوكهولم",
}


def pick(lang: str | None, default: str = "en") -> str:
    return lang if lang in LANGS else (default if default in LANGS else "en")


def t(lang: str, key: str, **values) -> str:
    return TEXT[pick(lang)].get(key, TEXT["en"].get(key, key)).format(**values)


def word(lang: str, value: str) -> str:
    """A saved code (a device, "direct", "internal", "local") in the reader's language; anything else as it is."""
    value = OLD.get(value, value or "")
    return t(lang, value) if value in TEXT["en"] else value


def country(lang: str, code: str, saved: str) -> str:
    if pick(lang) == "ar":
        return AR_COUNTRIES.get((code or "").upper(), saved or "")
    return code.upper() if saved and ARABIC.search(saved) and code else (saved or "")


def place(lang: str, name: str) -> str:
    """A city or region in the reader's language (Arabic for the known ones)."""
    name = OLD.get(name, name or "")
    if name == "local":
        return t(lang, "local")
    if pick(lang) == "ar":
        plain = name.lower().replace(" governorate", "").replace(" province", "").replace("-", " ").replace("'", "")
        return AR_CITIES.get(plain, name)
    return name


def ago(lang: str, seconds: float) -> str:
    if seconds < 60:
        return t(lang, "now")
    if seconds < 3600:
        return t(lang, "minutes", n=int(seconds // 60))
    if seconds < 86400:
        return t(lang, "hours", n=int(seconds // 3600))
    return t(lang, "days", n=int(seconds // 86400))
