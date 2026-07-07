"""
UTM tagging for BigTree Group spec-sheet PDFs.

Every category spec-sheet template maps to a fixed marketing campaign. When a PDF
is generated we append category-specific UTM parameters to every bigtree-group.com
link (footer, inquiry/add-to-cart, product "more info"), so GA4 can attribute the
visits / inquiries / sample requests / leads that originate from a downloaded PDF
back to the exact product category that produced them.

Rules honoured:
  1. Original path, query string and #fragment are preserved.
  2. Existing utm_* params are updated in place (never duplicated).
  4/5. Only bigtree-group.com hosts are touched; external domains are left alone.
  6. Output is always valid, properly URL-encoded (urllib does the encoding).
"""

import os
import re
import html as _htmllib
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

# Fixed UTM values shared by every spec-sheet PDF.
UTM_SOURCE = "specsheet_pdf"
UTM_MEDIUM = "pdf"
UTM_CONTENT = "specsheet"

# Template filename -> utm_campaign.
TEMPLATE_CAMPAIGN = {
    "specsheet-template__FURNITURE.html": "furniture",
    "specsheet-template__FABRIC.html": "fabric",
    "specsheet-template__FINE_ART.html": "fine_art",
    "specsheet-template__FLOOR_COVERING.html": "floor_covering",
    "specsheet-template__WALL_COVERING.html": "wall_covering",
    "specsheet-template__LEATHER.html": "leather",
    "specsheet-template__LIGHTING.html": "lighting",
    "specsheet-template__OBJECTS.html": "objects",
}

# UTM keys we manage (stripped before re-adding so updates don't duplicate).
_UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")

# Match the href value of an <a> tag only (leaves <img src> and other tags alone).
_HREF_RE = re.compile(r'(<a\b[^>]*?\shref=")([^"]*)(")', re.IGNORECASE)


def build_template_utm(template_filename):
    """Return the UTM dict for a template filename, or None if it isn't mapped."""
    campaign = TEMPLATE_CAMPAIGN.get(os.path.basename(template_filename))
    if not campaign:
        return None
    return {
        "utm_source": UTM_SOURCE,
        "utm_medium": UTM_MEDIUM,
        "utm_campaign": campaign,
        "utm_content": UTM_CONTENT,
    }


def _is_bigtree(host):
    host = host.lower()
    # Strip any :port
    host = host.split(":", 1)[0]
    return host == "bigtree-group.com" or host.endswith(".bigtree-group.com")


def add_utm_to_url(url, utm):
    """
    Append/refresh UTM params on a bigtree-group.com URL.

    Non-http(s) values (e.g. 'N/A', mailto:, {{ jinja }}) and external domains are
    returned unchanged. Path, non-UTM query params and #fragment are preserved.
    """
    if not url:
        return url
    try:
        parts = urlsplit(url)
    except ValueError:
        return url

    if parts.scheme not in ("http", "https") or not _is_bigtree(parts.netloc):
        return url

    # Keep every existing query param except the UTM ones we manage.
    query = [
        (k, v)
        for (k, v) in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in _UTM_KEYS
    ]
    for key in ("utm_source", "utm_medium", "utm_campaign", "utm_content"):
        if utm.get(key):
            query.append((key, utm[key]))

    path = parts.path or "/"  # root URL with no path -> "/" so "?..." is well-formed
    return urlunsplit((parts.scheme, parts.netloc, path, urlencode(query), parts.fragment))


def inject_utm_into_html(html, utm):
    """
    Rewrite every bigtree-group.com <a href> in an HTML string with the given UTM.

    Returns (new_html, count_updated, sample_url). count_updated only counts links
    that actually changed; sample_url is the first changed link (or None).
    """
    count = 0
    sample = {"url": None}

    def _repl(match):
        nonlocal count
        pre, raw, post = match.group(1), match.group(2), match.group(3)
        # The href is HTML-escaped in the rendered document (e.g. "&" -> "&amp;");
        # decode before parsing so query separators aren't misread, then re-escape.
        url = _htmllib.unescape(raw)
        new_url = add_utm_to_url(url, utm)
        if new_url == url:
            return match.group(0)  # unchanged (external / already-tagged): keep as-is
        count += 1
        escaped = new_url.replace("&", "&amp;")
        if sample["url"] is None:
            sample["url"] = new_url  # store the clean (decoded) URL for the report
        return pre + escaped + post

    return _HREF_RE.sub(_repl, html), count, sample["url"]
