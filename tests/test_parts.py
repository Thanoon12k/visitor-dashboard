import pytest

from visitor_dashboard import ua
from visitor_dashboard.geo import Geo, flag

CASES = {
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1":
        ("mobile", "iOS", "17.5", "Safari", "Apple", "iPhone", ""),
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0":
        ("desktop", "Windows", "10/11", "Edge", "", "", ""),
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36":
        ("mobile", "Android", "10", "Chrome", "", "", ""),
    "Mozilla/5.0 (Linux; Android 12; Redmi Note 11 Build/SKQ1) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0 Mobile Safari/537.36 Instagram 300.0":
        ("mobile", "Android", "12", "WebView", "Xiaomi", "Redmi Note 11", "Instagram"),
    "Mozilla/5.0 (Linux; Android 13; SM-X200) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36":
        ("tablet", "Android", "13", "Chrome", "Samsung", "SM-X200", ""),
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:127.0) Gecko/20100101 Firefox/127.0":
        ("desktop", "macOS", "10.15", "Firefox", "Apple", "Mac", ""),
    "TelegramBot (like TwitterBot)": ("bot", "", "", "", "", "", "Telegram"),
}


@pytest.mark.parametrize("agent", CASES)
def test_user_agents(agent):
    got = ua.parse(agent)
    assert (got["device"], got["os"], got["os_ver"], got["browser"], got["brand"], got["model"], got["app"]) == CASES[agent]


def test_empty_user_agent_is_a_bot():
    assert ua.parse("")["bot"]


@pytest.mark.parametrize("referrer,expected", [
    ("", "مباشر"), ("https://www.google.com/", "Google"), ("https://www.google.iq/search?q=x", "Google"),
    ("https://l.facebook.com/l.php?u=x", "Facebook"), ("https://m.facebook.com/", "Facebook"), ("https://t.me/x", "Telegram"),
    ("https://lnkd.in/abc", "LinkedIn"), ("https://t.co/abc", "X"), ("android-app://org.telegram.messenger/", "Telegram"),
    ("https://example.com/page", "example.com"), ("https://mysite.com/other", "داخلي"),
])
def test_sources(referrer, expected):
    assert ua.source(referrer, "mysite.com") == expected


def test_utm_wins():
    assert ua.source("https://www.google.com/", "mysite.com", "newsletter") == "newsletter"


def test_private_addresses_are_the_local_network():
    places = Geo(online=False).lookup(["192.168.1.5", "127.0.0.1", "8.8.8.8"])
    assert places["192.168.1.5"]["city"] == "شبكة محلية" and "8.8.8.8" not in places


def test_flag():
    assert flag("iq") == "🇮🇶" and flag("") == ""
