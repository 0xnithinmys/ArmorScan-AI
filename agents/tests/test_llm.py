from __future__ import annotations

from armorscan.llm import GroqResponsesClient


def test_extract_json_payload_from_output_text() -> None:
    client = GroqResponsesClient()
    payload = client._extract_json_payload({"output_text": '{"findings_drafts": []}'})
    assert payload == {"findings_drafts": []}


def test_extract_json_payload_from_output_chunks() -> None:
    client = GroqResponsesClient()
    payload = client._extract_json_payload(
        {
            "output": [
                {
                    "content": [
                        {"text": '{"findings_drafts": ['},
                        {"text": '{"id":"a","title":"x","severity":"low"}'},
                        {"text": "]}'"},
                    ]
                }
            ]
        }
    )
    assert payload == {"findings_drafts": [{"id": "a", "title": "x", "severity": "low"}]}
