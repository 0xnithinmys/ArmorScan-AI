from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urljoin

from armorscan.utils import normalize_target_url


async def run_browser_recon(target_url: str) -> dict[str, Any]:
    target_url = normalize_target_url(target_url)
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:
        return {
            "routes": [],
            "forms": [],
            "inputs": [],
            "observations": [],
            "errors": [f"Playwright unavailable: {exc}"],
        }

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-sandbox",
                ],
            )
            page = await browser.new_page(ignore_https_errors=True)
            requests: list[dict[str, Any]] = []
            responses: list[dict[str, Any]] = []

            page.on(
                "request",
                lambda request: requests.append(
                    {"url": request.url, "method": request.method, "resource_type": request.resource_type}
                ),
            )
            page.on(
                "response",
                lambda response: responses.append({"url": response.url, "status": response.status}),
            )

            response = await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_load_state("networkidle", timeout=8000)

            title = await page.title()
            final_url = page.url
            forms = await page.locator("form").evaluate_all(
                """forms => forms.map(form => ({
                    action: form.action || null,
                    method: (form.method || 'get').toLowerCase(),
                    input_count: form.querySelectorAll('input, textarea, select').length
                }))"""
            )
            inputs = await page.locator("input, textarea, select").evaluate_all(
                """nodes => nodes.map(node => ({
                    tag: node.tagName.toLowerCase(),
                    type: node.getAttribute('type'),
                    name: node.getAttribute('name'),
                    id: node.id || null,
                    placeholder: node.getAttribute('placeholder'),
                    aria_label: node.getAttribute('aria-label')
                })).slice(0, 50)"""
            )
            anchors = await page.locator("a[href]").evaluate_all(
                """links => links.map(link => link.href).filter(Boolean).slice(0, 100)"""
            )
            buttons = await page.locator("button, [role='button']").evaluate_all(
                """nodes => nodes.map(node => ({
                    text: (node.innerText || node.getAttribute('aria-label') || '').trim().slice(0, 80),
                    type: node.getAttribute('type')
                })).slice(0, 50)"""
            )
            accessibility_snapshot = await page.accessibility.snapshot()
            screenshot_bytes = await page.screenshot(full_page=False)
            await browser.close()

            routes = list(dict.fromkeys([final_url, *anchors, *[urljoin(target_url, path) for path in ["/"]]]))
            status = response.status if response else None
            return {
                "routes": routes,
                "forms": forms,
                "inputs": inputs,
                "observations": [
                    {
                        "url": final_url,
                        "title": title,
                        "status_code": status,
                        "buttons": buttons,
                        "requests": requests[:100],
                        "responses": responses[:100],
                        "accessibility_tree": accessibility_snapshot,
                        "screenshot_bytes": len(screenshot_bytes),
                    }
                ],
                "errors": [],
            }
    except Exception as exc:
        return {
            "routes": [],
            "forms": [],
            "inputs": [],
            "observations": [],
            "errors": [str(exc)],
        }


def run_browser_recon_sync(target_url: str) -> dict[str, Any]:
    return asyncio.run(run_browser_recon(target_url))
