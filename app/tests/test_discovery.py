from app.discovery import discover_links
from app.discovery.changedetection import DiffEngine
from app.discovery.watcher import WatchSource, Watcher
from app.storage import JsonStore
from app.http.fetch import FetchResult


class StubFetcher:
    def __init__(self, pages: list[str]) -> None:
        self._pages = pages

    def fetch(self, url: str, headers=None) -> FetchResult:
        html = self._pages.pop(0)
        return FetchResult(
            url=url,
            status=200,
            headers={},
            content=html.encode("utf-8"),
            encoding="utf-8",
        )


def test_discover_links_filters_duplicate_and_external() -> None:
    html = """
    <html>
      <body>
        <a href="/item/1">Item 1</a>
        <a href="https://example.com/item/1">Duplicate absolute</a>
        <a href="https://othersite.com/item/2">External</a>
      </body>
    </html>
    """
    links = discover_links(html, "https://example.com/home")
    assert links == ["https://example.com/item/1"]


def test_watcher_emits_initial_event_and_stores_state(tmp_path) -> None:
    url = "https://example.com/list"
    store = JsonStore(tmp_path / "state.json")

    fetcher = StubFetcher(
        [
            "<html><body>initial</body></html>",
            "<html><body>initial</body></html>",
        ]
    )

    watcher = Watcher(
        sources=[WatchSource(url=url, interval=10)],
        state_store=store,
        fetcher=fetcher,
        diff_engine=DiffEngine(min_change_ratio=0.0),
    )

    events = watcher.poll(now=0)
    assert len(events) == 1
    assert events[0].url == url
    assert "initial" in events[0].snapshot

    # Second poll within the interval should produce no new events.
    assert watcher.poll(now=11) == []
