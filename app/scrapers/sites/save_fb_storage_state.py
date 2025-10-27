from __future__ import annotations
from playwright.sync_api import sync_playwright
from pathlib import Path

# Where the browser session will be saved
STORAGE_PATH = Path("data/browser_storage/fb_storage_state.json")
STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    print("[init] Launching browser for Facebook login...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080})

        page = context.new_page()
        page.goto("https://www.facebook.com/login", timeout=60000)

        print(
            "\n[manual step] Please log in to Facebook manually in the opened browser.\n"
            "Once you are fully logged in and can access Marketplace, press ENTER here to save your session.\n"
        )
        input("Press ENTER when logged in and ready...")

        context.storage_state(path=str(STORAGE_PATH))
        print(f"[done] Saved Facebook login state → {STORAGE_PATH.resolve()}")

        browser.close()


if __name__ == "__main__":
    main()
