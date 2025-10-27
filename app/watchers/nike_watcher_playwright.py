import asyncio
import json
from datetime import datetime, timezone
from playwright.async_api import async_playwright
import aiofiles  # <--- async file I/O

# Optional import with fallback
try:
    from app.parsers.next_parser import parse_next_data  # type: ignore
except ImportError:

    def parse_next_data(path: str, source: str = "nike.com") -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[parser] Failed to load {path}: {e}")
            data = {}
        return {"source": source, "raw_payload": data}


async def fetch_nike_product(url: str) -> dict:
    """Render Nike PDP, extract __NEXT_DATA__, parse, and return structured listing."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"[NikeWatcher] Loading {url} ...")
        await page.goto(url, wait_until="networkidle")

        content = await page.evaluate(
            """() => {
            const el = document.querySelector('script#__NEXT_DATA__');
            return el ? el.textContent : null;
        }"""
        )

        if not content:
            print("__NEXT_DATA__ not found.")
            await browser.close()
            return {"error": "__NEXT_DATA__ not found."}

        tmp_path = "nike_next_data.json"
        async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
            await f.write(content)
        print(f"[NikeWatcher] Saved __NEXT_DATA__ → {tmp_path}")

        result = parse_next_data(tmp_path, source="nike.com")
        await browser.close()

        return {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "url": url,
            "payload": result,
        }


if __name__ == "__main__":
    url = "https://www.nike.com/t/air-force-1-07-mens-shoes-WrLlWX"
    data = asyncio.run(fetch_nike_product(url))
    print(json.dumps(data, indent=2))
