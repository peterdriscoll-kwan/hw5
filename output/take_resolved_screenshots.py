"""One-off script: drive the real running dashboard (frontend :5173, backend :8000)
with Playwright (system Chrome, no extra browser download) and save a real
screenshot of each resolved ticket for output/resolved_board.html.

Run manually: python output/take_resolved_screenshots.py
Requires both servers already running and all three tickets already resolved.
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT_DIR = Path(__file__).resolve().parent / "resolved_board_images"
OUT_DIR.mkdir(exist_ok=True)

TICKETS = [101, 102, 103]


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1000, "height": 900})
        page.goto("http://localhost:5173")
        page.wait_for_selector(".tray__list")

        for i, ticket_id in enumerate(TICKETS):
            buttons = page.query_selector_all(".tray__list button")
            buttons[i].click()
            page.wait_for_timeout(600)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(200)
            path = OUT_DIR / f"ticket_{ticket_id}.png"
            page.screenshot(path=str(path))
            print(f"saved {path}")

        browser.close()


if __name__ == "__main__":
    main()
