"""Reading a visit without any service: the device from the User-Agent, and where the visitor came from.

parse(ua) -> {device, os, os_ver, browser, browser_ver, brand, model, app, bot}
source(referrer, host, utm) -> a short name such as "Google", "Facebook", "Telegram", "مباشر" or the site's domain.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

BOTS = re.compile(
    r"bot\b|bot/|crawl|spider|slurp|scrap|fetch|monitor|preview|lighthouse|pagespeed|headless|phantom|selenium|playwright"
    r"|facebookexternalhit|facebookcatalog|meta-externalagent|whatsapp/|telegrambot|discordbot|skypeuripreview|embedly"
    r"|curl/|wget/|python-requests|python-urllib|aiohttp|httpx|go-http-client|okhttp|java/|libwww|axios/|node-fetch"
    r"|uptimerobot|pingdom|statuscake|ahrefs|semrush|mj12|dotbot|petalbot|bytespider|gptbot|claudebot|ccbot|chatgpt"
    r"|perplexity|amazonbot|applebot|yandex|baiduspider|duckduckbot|bingpreview|googleother|google-inspectiontool",
    re.I)
# the app a link was opened inside (its own browser)
APPS = (("Facebook", r"FBAN|FBAV|FB_IAB|FBIOS"), ("Instagram", r"Instagram"), ("Messenger", r"MessengerForiOS|FB_MSGR"),
        ("TikTok", r"musical_ly|BytedanceWebview|TikTok"), ("Snapchat", r"Snapchat"), ("LinkedIn", r"LinkedInApp"),
        ("Telegram", r"Telegram"), ("WhatsApp", r"WhatsApp"), ("X", r"Twitter"), ("Line", r"\bLine/"),
        ("Gmail", r"GSA/|GoogleApp"))
BROWSERS = (("Edge", r"Edg(?:e|A|iOS)?/([\d.]+)"), ("Opera", r"(?:OPR|OPT|Opera)/([\d.]+)"),
            ("Samsung Internet", r"SamsungBrowser/([\d.]+)"), ("Yandex", r"YaBrowser/([\d.]+)"),
            ("UC Browser", r"UCBrowser/([\d.]+)"), ("Huawei Browser", r"HuaweiBrowser/([\d.]+)"),
            ("Mi Browser", r"(?:XiaoMi/)?MiuiBrowser/([\d.]+)"), ("Firefox", r"(?:Firefox|FxiOS)/([\d.]+)"),
            ("Chrome", r"CriOS/([\d.]+)"), ("Chrome", r"Chrome/([\d.]+)"), ("Safari", r"Version/([\d.]+).*Safari/"))
# the first letters of an Android model -> its maker
BRANDS = (("Samsung", r"SM-|GT-|SAMSUNG|Galaxy"), ("Xiaomi", r"Redmi|Mi |MI |POCO|M\d{4}|2\d{3}[A-Z0-9]{4,}|Xiaomi"),
          ("Huawei", r"HUAWEI|[A-Z]{3}-(?:L|AL|TL|LX|NX)\d|Mate|nova"), ("Honor", r"HONOR|HRY-|ANY-|CRT-"),
          ("OPPO", r"CPH\d|OPPO"), ("Realme", r"RMX\d|realme"), ("vivo", r"vivo|V2\d{3}"), ("Infinix", r"Infinix"),
          ("Tecno", r"TECNO"), ("itel", r"itel"), ("Google", r"Pixel"), ("Motorola", r"moto|Motorola|XT\d{4}"),
          ("OnePlus", r"OnePlus|ONEPLUS|[A-Z]{2}\d{4}$"), ("Nokia", r"Nokia|TA-\d"), ("Lenovo", r"Lenovo"),
          ("Sony", r"Xperia|SO-\d"), ("LG", r"LG-|LM-"), ("ZTE", r"ZTE"), ("Asus", r"ASUS|ZenFone"))
OS_NAMES = (("Windows", r"Windows NT ([\d.]+)"), ("Android", r"Android ([\d.]+)"), ("iOS", r"(?:iPhone|CPU) OS ([\d_]+)"),
            ("iPadOS", r"iPad.*OS ([\d_]+)"), ("macOS", r"Mac OS X ([\d_.]+)"), ("ChromeOS", r"CrOS \S+ ([\d.]+)"),
            ("HarmonyOS", r"HarmonyOS ?([\d.]*)"), ("Linux", r"Linux()"))
WINDOWS = {"10.0": "10/11", "6.3": "8.1", "6.2": "8", "6.1": "7", "6.0": "Vista", "5.1": "XP"}


def parse(ua: str) -> dict:
    ua = ua or ""
    out = {"device": "desktop", "os": "", "os_ver": "", "browser": "", "browser_ver": "", "brand": "", "model": "",
           "app": "", "bot": not ua.strip() or bool(BOTS.search(ua))}
    for name, pattern in OS_NAMES:
        if name == "iOS" and "iPad" in ua:
            continue
        found = re.search(pattern, ua)
        if found:
            out["os"], out["os_ver"] = name, found.group(1).replace("_", ".")
            if name == "Windows":
                out["os_ver"] = WINDOWS.get(out["os_ver"], out["os_ver"])
            break
    for name, pattern in APPS:
        if re.search(pattern, ua):
            out["app"] = name
            break
    for name, pattern in BROWSERS:
        found = re.search(pattern, ua)
        if found:
            out["browser"], out["browser_ver"] = name, found.group(1).split(".")[0]
            break
    if out["os"] == "Android" and out["browser"] == "Chrome" and ("; wv)" in ua or out["app"]):
        out["browser"] = "WebView"
    if out["bot"]:
        out["device"] = "bot"
    elif "iPad" in ua or "Tablet" in ua or (out["os"] == "Android" and "Mobile" not in ua):
        out["device"] = "tablet"
    elif re.search(r"Mobi|iPhone|iPod|Android|Opera Mini|IEMobile", ua):
        out["device"] = "mobile"
    if "iPhone" in ua or "iPad" in ua:
        out["brand"], out["model"] = "Apple", "iPhone" if "iPhone" in ua else "iPad"
    elif "Macintosh" in ua:
        out["brand"], out["model"] = "Apple", "Mac"
    elif out["os"] == "Android":
        found = re.search(r"Android [\d.]+;(?: [a-z]{2}[-_][a-zA-Z]{2};)? ([^;)]+?)(?: Build/[^;)]*)?(?:;[^)]*)?\)", ua)
        model = found.group(1).strip() if found else ""
        if model and model not in ("K", "Mobile", "wv") and not model.startswith("Linux"):
            out["model"] = model
            out["brand"] = next((b for b, p in BRANDS if re.search(p, model)), "")
    return out


# where a visitor came from: a host suffix -> its name
SOURCES = (("Google", ("google.", "googleusercontent.com", "android-app://com.google")), ("Bing", ("bing.com",)),
           ("Yahoo", ("yahoo.",)), ("DuckDuckGo", ("duckduckgo.com",)), ("Yandex", ("yandex.",)),
           ("Facebook", ("facebook.com", "fb.com", "fb.me", "android-app://com.facebook")),
           ("Instagram", ("instagram.com",)), ("Telegram", ("t.me", "telegram.org", "telegram.me", "org.telegram")),
           ("WhatsApp", ("whatsapp.com", "wa.me", "com.whatsapp")), ("LinkedIn", ("linkedin.com", "lnkd.in")),
           ("X", ("t.co", "twitter.com", "x.com")), ("YouTube", ("youtube.com", "youtu.be")),
           ("TikTok", ("tiktok.com",)), ("GitHub", ("github.com", "github.io")), ("Reddit", ("reddit.com",)),
           ("ChatGPT", ("chatgpt.com", "openai.com")), ("Claude", ("claude.ai",)), ("Gmail", ("mail.google.com",)))


def source(referrer: str, host: str = "", utm: str = "") -> str:
    """The visit's origin: utm_source when the link carries it, else the referring site (named when it is known)."""
    if utm:
        return utm.strip()[:60]
    if not referrer:
        return "مباشر"
    where = urlsplit(referrer)
    ref_host = (where.hostname or "").lower().removeprefix("www.").removeprefix("m.").removeprefix("l.")
    if referrer.startswith("android-app://"):
        ref_host = referrer[len("android-app://"):].split("/")[0]
    if host and ref_host == host.lower().split(":")[0].removeprefix("www."):
        return "داخلي"
    for name, hosts in SOURCES:
        if any(ref_host == h or ref_host.endswith("." + h) or (h.endswith(".") and (ref_host.startswith(h) or f".{h}" in ref_host))
               or (not h.endswith(".") and h in referrer and h.startswith(("android-app", "com.", "org."))) for h in hosts):
            return name
    return ref_host or "مباشر"
