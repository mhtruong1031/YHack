"""Notify external API after a sort (URL from config)."""

import logging

import requests

import config

logger = logging.getLogger(__name__)


def notify_sort_result(label: str, extra: dict | None = None) -> None:
    """
    POST sort outcome to API_BASE_URL.
    If URL is empty, log only (no network).
    """
    url = (config.API_BASE_URL or "").strip()
    if not url:
        logger.info("api_client: API_BASE_URL unset; skip POST (label=%s)", label)
        return

    payload = {"classification": label, **(extra or {})}
    headers = {}
    key = config.get_api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    try:
        r = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=config.API_TIMEOUT_SEC,
        )
        r.raise_for_status()
        logger.info("api_client: POST ok %s", r.status_code)
    except requests.RequestException as e:
        logger.error("api_client: POST failed: %s", e)


def notify_drop_image(jpeg_bytes: bytes, classification: str | None = None) -> None:
    """
    POST multipart/form-data: field ``image`` (frame.jpg, image/jpeg), optional
    ``classification`` text. Bearer from ``DROP_API_KEY`` or ``DEVICE_INGEST_SECRET``.
    """
    url = (config.DROP_API_URL or "").strip()
    if not url:
        logger.info(
            "api_client: DROP_API_URL unset; skip drop image POST (classification=%s)",
            classification,
        )
        return

    files = {
        "image": ("frame.jpg", jpeg_bytes, "image/jpeg"),
    }
    data = {}
    if classification is not None:
        data["classification"] = classification

    headers = {}
    key = config.get_drop_api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    else:
        logger.warning(
            "api_client: drop ingest URL set but no secret; set DROP_API_KEY or "
            "DEVICE_INGEST_SECRET (401 likely)"
        )

    try:
        r = requests.post(
            url,
            files=files,
            data=data,
            headers=headers,
            timeout=config.API_TIMEOUT_SEC,
        )
        r.raise_for_status()
        logger.info("api_client: drop image POST ok %s", r.status_code)
    except requests.RequestException as e:
        logger.error("api_client: drop image POST failed: %s", e)
