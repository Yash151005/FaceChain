"""
reverse_search.py — Real Reverse Image Search via SerpAPI (Google Lens)

Uploads a local face image to SerpAPI, performs a Google Lens reverse-image
search, and returns the best matching public URL with page title and domain.

All results are *live* API responses — nothing is hardcoded.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

from serpapi import Client


class NoMatchFoundError(Exception):
    """Raised when the reverse image search returns no usable matches."""
    pass


class SearchAPIError(Exception):
    """Raised when the SerpAPI request fails (network, auth, quota, etc.)."""
    pass


def search_face(image_path: str, api_key: str) -> dict:
    """
    Perform a real Google Lens reverse-image search for a local image file.

    Parameters
    ----------
    image_path : str
        Path to the face image (JPG/PNG/WebP, ≤ 500 KB recommended).
    api_key : str
        A valid SerpAPI API key.

    Returns
    -------
    dict
        {
            "url":       str,       # Best-matching public page URL
            "title":     str,       # Page title / match description
            "domain":    str,       # Source domain (e.g. "instagram.com")
            "thumbnail": str|None,  # Thumbnail URL if available
        }

    Raises
    ------
    FileNotFoundError
        If *image_path* does not exist.
    SearchAPIError
        If the SerpAPI request fails for any reason.
    NoMatchFoundError
        If no usable visual matches are found.
    """
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if not api_key or not api_key.strip():
        raise SearchAPIError("SerpAPI key is missing or empty. Check your .env file.")

    try:
        client = Client(api_key=api_key.strip())

        # Step 1: Upload the local image to SerpAPI (returns a temp image_id)
        upload_result = client.upload_image(str(path))
        image_id = upload_result.get("image_id")

        if not image_id:
            raise SearchAPIError(
                "SerpAPI image upload did not return an image_id. "
                "Ensure the image is a valid JPG/PNG/WebP under 500 KB."
            )

        # Step 2: Perform Google Lens search with the uploaded image
        results = client.search({
            "engine": "google_lens",
            "image_id": image_id,
        })

    except FileNotFoundError:
        raise
    except NoMatchFoundError:
        raise
    except SearchAPIError:
        raise
    except Exception as exc:
        raise SearchAPIError(f"SerpAPI request failed: {exc}") from exc

    # Step 3: Parse results — look for visual matches first, then knowledge graph
    match = _extract_best_match(results)
    if match is None:
        raise NoMatchFoundError(
            "No matching public pages found for this face image. "
            "Try a more recognizable or higher-resolution photo."
        )

    return match


def _extract_best_match(results: dict) -> dict | None:
    """
    Walk through SerpAPI Google Lens response and find the best visual match.

    Priority order:
    1. visual_matches — direct page matches
    2. knowledge_graph — entity matches (celebrities, public figures)
    3. organic_results — fallback text-based results
    """

    # --- 1. Visual Matches (most relevant) ---
    visual_matches = results.get("visual_matches", [])
    for item in visual_matches:
        url = item.get("link") or item.get("url")
        title = item.get("title", "")
        source = item.get("source", "")
        thumbnail = item.get("thumbnail")

        if url and _is_valid_url(url):
            domain = _extract_domain(url)
            return {
                "url": url,
                "title": title or "Untitled Page",
                "domain": domain or source or "unknown",
                "thumbnail": thumbnail,
            }

    # --- 2. Knowledge Graph ---
    kg = results.get("knowledge_graph", {})
    if kg:
        # Knowledge graph sometimes has a link or source
        kg_link = kg.get("link") or kg.get("source", {}).get("link")
        kg_title = kg.get("title", "")
        if kg_link and _is_valid_url(kg_link):
            return {
                "url": kg_link,
                "title": kg_title or "Knowledge Graph Result",
                "domain": _extract_domain(kg_link),
                "thumbnail": kg.get("thumbnail"),
            }

    # --- 3. Organic Results (fallback) ---
    organic = results.get("organic_results", [])
    for item in organic:
        url = item.get("link")
        title = item.get("title", "")
        if url and _is_valid_url(url):
            return {
                "url": url,
                "title": title or "Search Result",
                "domain": _extract_domain(url),
                "thumbnail": item.get("thumbnail"),
            }

    return None


def _is_valid_url(url: str) -> bool:
    """Return True if *url* looks like a usable HTTP(S) URL."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _extract_domain(url: str) -> str:
    """Extract the domain from a URL, stripping 'www.' prefix."""
    try:
        domain = urlparse(url).netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return "unknown"
