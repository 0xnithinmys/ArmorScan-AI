from __future__ import annotations


def normalize_target_url(target_url: str) -> str:
    if "://" not in target_url:
        return f"https://{target_url}"
    return target_url
