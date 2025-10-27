from pathlib import Path

import pytest


class DummyPage:
    def __init__(self, workdir: Path):
        self._workdir = workdir
        self.goto_calls: list[tuple[str, str | None]] = []
        self.screenshot_paths: list[Path] = []

    def goto(self, url: str, wait_until: str | None = None) -> None:
        self.goto_calls.append((url, wait_until))

    def screenshot(self, path: str) -> None:
        target = Path(path)
        target.write_text("fake-image", encoding="utf-8")
        self.screenshot_paths.append(target)


class DummyContext:
    def __init__(self, page: DummyPage):
        self._page = page
        self.closed = False

    def new_page(self) -> DummyPage:
        return self._page

    def close(self) -> None:
        self.closed = True


class DummyBrowser:
    def __init__(self, page: DummyPage):
        self._page = page
        self.closed = False

    def new_context(self) -> DummyContext:
        return DummyContext(self._page)

    def close(self) -> None:
        self.closed = True


class FakePlaywright:
    def __init__(self, browser: DummyBrowser):
        self._browser = browser

    def __enter__(self) -> "FakePlaywright":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    class Chromium:
        def __init__(self, browser: DummyBrowser):
            self._browser = browser

        def launch(self, headless: bool = True):
            return self._browser

    @property
    def chromium(self) -> "FakePlaywright.Chromium":
        return FakePlaywright.Chromium(self._browser)


def test_fetch_and_screenshot_makes_local_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.scraper import playwright_client

    page = DummyPage(tmp_path)
    browser = DummyBrowser(page)

    monkeypatch.setattr(
        playwright_client, "sync_playwright", lambda: FakePlaywright(browser)
    )
    monkeypatch.setattr(playwright_client, "ensure_screenshot_dir", lambda: tmp_path)

    result = playwright_client.fetch_and_screenshot(
        "https://mocksite.test/item/1", name="mock.png"
    )

    assert result is not None
    assert result.name == "mock.png"
    assert result.exists()

    assert page.goto_calls == [("https://mocksite.test/item/1", "networkidle")]
    assert page.screenshot_paths and page.screenshot_paths[0] == result
    assert browser.closed is True
