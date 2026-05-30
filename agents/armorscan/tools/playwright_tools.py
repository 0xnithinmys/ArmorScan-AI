from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urljoin, urlparse

from armorscan.policy import evaluate_agent_action
from armorscan.utils import normalize_target_url


async def _capture_page_surface(page, target_url: str) -> dict[str, Any]:
    errors: list[str] = []
    response = None
    final_url = target_url
    title = ""
    forms: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    upload_inputs: list[dict[str, Any]] = []
    anchors: list[str] = []
    scripts: list[str] = []
    buttons: list[dict[str, Any]] = []
    clickable_surfaces: list[dict[str, Any]] = []
    accessibility_snapshot: Any = None
    screenshot_bytes = b""

    try:
        response = await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
    except Exception as exc:
        errors.append(f"navigation failed: {type(exc).__name__}: {exc!r}")
        return {
            "url": target_url,
            "title": title,
            "status_code": None,
            "buttons": buttons,
            "scripts": scripts,
            "uploads": upload_inputs,
            "clickable_surfaces": clickable_surfaces,
            "requests": [],
            "responses": [],
            "accessibility_tree": accessibility_snapshot,
            "screenshot_bytes": 0,
            "forms": forms,
            "inputs": inputs,
            "anchors": anchors,
            "final_url": final_url,
            "errors": errors,
        }

    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception as exc:
        errors.append(f"network idle wait failed: {type(exc).__name__}: {exc!r}")

    try:
        title = await page.title()
    except Exception as exc:
        errors.append(f"title read failed: {type(exc).__name__}: {exc!r}")

    try:
        final_url = page.url
    except Exception as exc:
        errors.append(f"final URL read failed: {type(exc).__name__}: {exc!r}")

    try:
        forms = await page.locator("form").evaluate_all(
            """forms => forms.map(form => ({
                action: form.action || null,
                method: (form.method || 'get').toLowerCase(),
                input_count: form.querySelectorAll('input, textarea, select').length
            }))"""
        )
    except Exception as exc:
        errors.append(f"form extraction failed: {type(exc).__name__}: {exc!r}")

    try:
        inputs = await page.locator("input, textarea, select").evaluate_all(
            """nodes => nodes.map(node => {
                const type = node.getAttribute('type');
                const name = node.getAttribute('name');
                const id = node.id || null;
                const placeholder = node.getAttribute('placeholder');
                const ariaLabel = node.getAttribute('aria-label');
                const autocomplete = node.getAttribute('autocomplete');
                const role = node.getAttribute('role');
                const haystack = [type, name, id, placeholder, ariaLabel, autocomplete, role].filter(Boolean).join(' ').toLowerCase();
                const purpose = /search|query|filter|find/.test(haystack) ? 'search' : (/password|passcode|secret/.test(haystack) ? 'auth' : 'generic');
                return {
                    tag: node.tagName.toLowerCase(),
                    type,
                    name,
                    id,
                    placeholder,
                    aria_label: ariaLabel,
                    autocomplete,
                    role,
                    purpose
                };
            }).slice(0, 60)"""
        )
    except Exception as exc:
        errors.append(f"input extraction failed: {type(exc).__name__}: {exc!r}")

    upload_inputs = [item for item in inputs if str(item.get("type") or "").lower() == "file"]

    try:
        anchors = await page.locator("a[href]").evaluate_all(
            """links => links.map(link => link.href).filter(Boolean).slice(0, 120)"""
        )
    except Exception as exc:
        errors.append(f"anchor extraction failed: {type(exc).__name__}: {exc!r}")

    try:
        scripts = await page.locator("script[src]").evaluate_all(
            """scripts => scripts.map(script => script.src).filter(Boolean).slice(0, 120)"""
        )
    except Exception as exc:
        errors.append(f"script extraction failed: {type(exc).__name__}: {exc!r}")

    try:
        buttons = await page.locator("button, [role='button']").evaluate_all(
            """nodes => nodes.map(node => ({
                text: (node.innerText || node.getAttribute('aria-label') || '').trim().slice(0, 80),
                type: node.getAttribute('type')
            })).slice(0, 50)"""
        )
    except Exception as exc:
        errors.append(f"button extraction failed: {type(exc).__name__}: {exc!r}")

    try:
        clickable_surfaces = await _explore_safe_clicks(page, target_url)
    except Exception as exc:
        errors.append(f"clickable surface exploration failed: {type(exc).__name__}: {exc!r}")

    try:
        accessibility_snapshot = await page.accessibility.snapshot()
    except Exception as exc:
        errors.append(f"accessibility snapshot failed: {type(exc).__name__}: {exc!r}")

    try:
        screenshot_bytes = await page.screenshot(full_page=False)
    except Exception as exc:
        errors.append(f"screenshot failed: {type(exc).__name__}: {exc!r}")

    return {
        "url": final_url,
        "title": title,
        "status_code": response.status if response else None,
        "buttons": buttons,
        "scripts": scripts,
        "uploads": upload_inputs,
        "clickable_surfaces": clickable_surfaces,
        "requests": [],
        "responses": [],
        "accessibility_tree": accessibility_snapshot,
        "screenshot_bytes": len(screenshot_bytes),
        "forms": forms,
        "inputs": inputs,
        "anchors": anchors,
        "final_url": final_url,
        "errors": errors,
    }


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

            page_snapshots: list[dict[str, Any]] = []
            visited: set[str] = set()

            async def visit(url: str) -> None:
                normalized = normalize_target_url(url)
                if normalized in visited or len(page_snapshots) >= 6:
                    return
                visited.add(normalized)
                snapshot = await _capture_page_surface(page, normalized)
                if requests:
                    snapshot["requests"] = requests[:100]
                if responses:
                    snapshot["responses"] = responses[:100]
                page_snapshots.append(snapshot)

            await visit(target_url)

            crawl_candidates: list[str] = []
            if page_snapshots:
                first_snapshot = page_snapshots[0]
                crawl_candidates.extend(
                    link for link in first_snapshot.get("anchors", []) if isinstance(link, str) and link
                )
                crawl_candidates.extend(
                    urljoin(target_url.rstrip("/") + "/", path.lstrip("/"))
                    for path in ["/login", "/search", "/api", "/health", "/graphql"]
                )

            for candidate in crawl_candidates:
                if len(page_snapshots) >= 6:
                    break
                if not candidate or not _same_host(target_url, candidate):
                    continue
                if any(candidate.endswith(blocked) for blocked in (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg")):
                    continue
                try:
                    await visit(candidate)
                except Exception:
                    continue

            await browser.close()

            routes: list[str] = []
            forms: list[dict[str, Any]] = []
            inputs: list[dict[str, Any]] = []
            scripts: list[str] = []
            upload_inputs: list[dict[str, Any]] = []
            clickable_surfaces: list[dict[str, Any]] = []
            for snapshot in page_snapshots:
                routes.extend(
                    [
                        snapshot.get("final_url") or snapshot.get("url"),
                        *snapshot.get("anchors", []),
                        *[item["url"] for item in snapshot.get("clickable_surfaces", []) if item.get("url")],
                    ]
                )
                forms.extend(snapshot.get("forms", []))
                inputs.extend(snapshot.get("inputs", []))
                scripts.extend(snapshot.get("scripts", []))
                upload_inputs.extend(snapshot.get("uploads", []))
                clickable_surfaces.extend(snapshot.get("clickable_surfaces", []))

            routes = list(dict.fromkeys([route for route in routes if route]))
            clickable_surfaces = clickable_surfaces[:30]
            return {
                "routes": routes,
                "forms": forms,
                "inputs": inputs,
                "uploads": upload_inputs,
                "scripts": scripts,
                "clickable_surfaces": clickable_surfaces,
                "observations": [
                    {
                        **snapshot,
                        "requests": requests[:100],
                        "responses": responses[:100],
                    }
                    for snapshot in page_snapshots
                ],
                "errors": [error for snapshot in page_snapshots for error in snapshot.get("errors", [])],
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
