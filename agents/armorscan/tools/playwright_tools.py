from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urljoin, urlparse

from armorscan.policy import evaluate_agent_action
from armorscan.utils import normalize_target_url


async def run_browser_recon(
    target_url: str,
    *,
    intent_plan: dict[str, Any] | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    target_url = normalize_target_url(target_url)
    decision = evaluate_agent_action(
        intent_plan=intent_plan,
        token=token,
        action="browser.navigate",
        url=target_url,
    )
    if not decision.allowed:
        return {
            "routes": [],
            "forms": [],
            "inputs": [],
            "uploads": [],
            "scripts": [],
            "clickable_surfaces": [],
            "observations": [],
            "errors": [decision.reason],
            "policy_decisions": [decision.as_dict()],
        }

    try:
        from playwright.async_api import async_playwright
    except Exception as exc:
        return {
            "routes": [],
            "forms": [],
            "inputs": [],
            "uploads": [],
            "scripts": [],
            "clickable_surfaces": [],
            "observations": [],
            "errors": [f"Playwright unavailable: {exc}"],
            "policy_decisions": [decision.as_dict()],
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
            upload_inputs = [
                item for item in inputs if str(item.get("type") or "").lower() == "file"
            ]
            anchors = await page.locator("a[href]").evaluate_all(
                """links => links.map(link => link.href).filter(Boolean).slice(0, 100)"""
            )
            scripts = await page.locator("script[src]").evaluate_all(
                """scripts => scripts.map(script => script.src).filter(Boolean).slice(0, 100)"""
            )
            buttons = await page.locator("button, [role='button']").evaluate_all(
                """nodes => nodes.map(node => ({
                    text: (node.innerText || node.getAttribute('aria-label') || '').trim().slice(0, 80),
                    type: node.getAttribute('type')
                })).slice(0, 50)"""
            )
            clickable_surfaces = await _explore_safe_clicks(page, target_url)
            accessibility_snapshot = await page.accessibility.snapshot()
            screenshot_bytes = await page.screenshot(full_page=False)
            await browser.close()

            routes = list(
                dict.fromkeys(
                    [
                        final_url,
                        *anchors,
                        *[item["url"] for item in clickable_surfaces if item.get("url")],
                        *[urljoin(target_url, path) for path in ["/"]],
                    ]
                )
            )
            status = response.status if response else None
            return {
                "routes": routes,
                "forms": forms,
                "inputs": inputs,
                "uploads": upload_inputs,
                "scripts": scripts,
                "clickable_surfaces": clickable_surfaces,
                "observations": [
                    {
                        "url": final_url,
                        "title": title,
                        "status_code": status,
                        "buttons": buttons,
                        "scripts": scripts,
                        "uploads": upload_inputs,
                        "clickable_surfaces": clickable_surfaces,
                        "requests": requests[:100],
                        "responses": responses[:100],
                        "accessibility_tree": accessibility_snapshot,
                        "screenshot_bytes": len(screenshot_bytes),
                    }
                ],
                "errors": [],
                "policy_decisions": [decision.as_dict()],
            }
    except Exception as exc:
        return {
            "routes": [],
            "forms": [],
            "inputs": [],
            "uploads": [],
            "scripts": [],
            "clickable_surfaces": [],
            "observations": [],
            "errors": [str(exc)],
            "policy_decisions": [decision.as_dict()],
        }


def run_browser_recon_sync(
    target_url: str,
    *,
    intent_plan: dict[str, Any] | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    return asyncio.run(run_browser_recon(target_url, intent_plan=intent_plan, token=token))


async def _explore_safe_clicks(page, target_url: str) -> list[dict[str, Any]]:
    base_host = urlparse(target_url).hostname
    surfaces: list[dict[str, Any]] = []
    locators = await page.locator("a[href], button, [role='button']").evaluate_all(
        """nodes => nodes.map((node, index) => ({
            index,
            tag: node.tagName.toLowerCase(),
            text: (node.innerText || node.getAttribute('aria-label') || '').trim().slice(0, 80),
            href: node.href || null,
            type: node.getAttribute('type'),
            disabled: Boolean(node.disabled || node.getAttribute('aria-disabled') === 'true')
        })).slice(0, 30)"""
    )
    for item in locators:
        href = item.get("href")
        if href:
            parsed = urlparse(href)
            if parsed.hostname == base_host:
                surfaces.append(
                    {
                        "kind": "navigation",
                        "url": href,
                        "text": item.get("text"),
                        "tag": item.get("tag"),
                    }
                )
            continue
        if str(item.get("type") or "").lower() == "submit":
            surfaces.append(
                {
                    "kind": "form-submit-control",
                    "text": item.get("text"),
                    "tag": item.get("tag"),
                    "safe_clicked": False,
                    "reason": "submit controls are cataloged but not clicked during safe recon",
                }
            )
        elif not item.get("disabled"):
            surfaces.append(
                {
                    "kind": "interactive-control",
                    "text": item.get("text"),
                    "tag": item.get("tag"),
                    "safe_clicked": False,
                    "reason": "click exploration is metadata-only unless an explicit auth workflow is configured",
                }
            )
    return surfaces[:30]
