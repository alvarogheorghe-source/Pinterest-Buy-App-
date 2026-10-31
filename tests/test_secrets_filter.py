"""Geheime Schlüssel tauchen nie in Fehlermeldungen, Warnungen oder Logs auf."""

import logging

from backend import products, secrets_filter


def test_keys_from_env_and_urls_are_removed(monkeypatch):
    monkeypatch.setenv("ALIEXPRESS_APP_KEY", "ali-key-123456")
    monkeypatch.setenv("AWIN_FEED_KEY", "awinfeedkey987")
    monkeypatch.setenv("AMAZON_PARTNER_TAG", "malipin-21")          # kein Geheimnis -> bleibt
    text = ("Client error '400' for url 'https://api-sg.aliexpress.com/sync?app_key=ali-key-123456"
            "&sign=ABCDEF0123&method=x' | https://productdata.awin.com/datafeed/download/apikey/"
            "awinfeedkey987/de/ | Authorization: Bearer abcdefghijklmnop | tag=malipin-21")
    clean = secrets_filter.redact(text)
    assert "ali-key-123456" not in clean and "awinfeedkey987" not in clean
    assert "ABCDEF0123" not in clean and "abcdefghijklmnop" not in clean
    assert "app_key=***" in clean and "/apikey/***/" in clean and "malipin-21" in clean


def test_log_lines_are_cleaned(monkeypatch, caplog):
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "ebay-secret-xyz")
    secrets_filter.install()
    with caplog.at_level(logging.WARNING):
        logging.getLogger("test").warning("eBay sagt nein: %s", "token ebay-secret-xyz abgelehnt")
        try:
            raise RuntimeError("kaputt bei ?access_token=ebay-secret-xyz")
        except RuntimeError:
            logging.getLogger("test").exception("Fehler")
    assert "ebay-secret-xyz" not in caplog.text and "***" in caplog.text


def test_shop_warnings_for_the_browser_are_cleaned(monkeypatch):
    monkeypatch.setenv("ETSY_API_KEY", "etsy-key-555555")

    class Broken(products.ProductSource):
        name = "etsy"

        def load(self):
            raise products.ProductSourceError("Etsy: 403 for https://x.example/?api_key=etsy-key-555555")

    class Fine(products.ProductSource):
        def load(self):
            return []

    source = products.CombinedSource([Broken(), Fine()])
    source.load()
    assert "etsy-key-555555" not in str(source.warnings())
