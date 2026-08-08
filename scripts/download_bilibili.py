#!/usr/bin/env python3
"""
Download Bilibili video audio or AI subtitles for a single part.

Uses direct Bilibili APIs to avoid the intermittent HTTP 412 anti-crawler
errors that break yt-dlp, with yt-dlp as a fallback.

Outputs into <output_dir>:
  metadata.json   - full metadata from the view API
  subtitle.txt    - AI subtitle text (only if subtitles available)
  audio.m4a       - DASH audio stream (only if no subtitles)
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
)
VIEW_API = "https://api.bilibili.com/x/web-interface/view"
PLAYER_API = "https://api.bilibili.com/x/player/wbi/v2"
PLAYURL_API = "https://api.bilibili.com/x/player/playurl"


def build_headers(url: str) -> dict:
    return {
        "User-Agent": USER_AGENT,
        "Referer": url,
        "Origin": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }


def parse_url(url: str) -> tuple:
    """Extract BV id and optional page index from a bilibili video URL."""
    m = re.search(r"(BV[0-9A-Za-z]{10})", url)
    if not m:
        raise ValueError(f"Not a valid bilibili video URL: {url}")
    bvid = m.group(1)
    p_match = re.search(r"[?&]p=(\d+)", url)
    p = int(p_match.group(1)) if p_match else 1
    return bvid, p


def get_view_info(bvid: str, referer: str) -> dict:
    """Fetch video metadata from the view API."""
    resp = requests.get(
        VIEW_API, params={"bvid": bvid}, headers=build_headers(referer), timeout=30
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"View API error: {data.get('code')} {data.get('message')}")
    return data["data"]


def select_page(view_info: dict, p: int) -> dict:
    """Pick the requested page from a multi-part anthology."""
    pages = view_info.get("pages", [])
    if not pages:
        raise RuntimeError("No pages found in view data")
    if p < 1 or p > len(pages):
        raise ValueError(
            f"Page {p} out of range. This video has {len(pages)} parts."
        )
    return pages[p - 1]


def get_subtitles(view_info: dict, page: dict, referer: str) -> list:
    """Return subtitle entries for a page, or empty list if none."""
    try:
        resp = requests.get(
            PLAYER_API,
            params={"aid": view_info["aid"], "cid": page["cid"]},
            headers=build_headers(referer),
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            return []
        return data.get("data", {}).get("subtitle", {}).get("subtitles", []) or []
    except Exception:
        return []


def download_subtitle(subtitle: dict, output_dir: Path, referer: str) -> Path:
    """Download a subtitle JSON and save plain text to subtitle.txt."""
    sub_url = subtitle.get("subtitle_url", "")
    if sub_url.startswith("//"):
        sub_url = "https:" + sub_url
    if not sub_url:
        raise RuntimeError("Subtitle entry has no url")

    resp = requests.get(sub_url, headers=build_headers(referer), timeout=30)
    resp.raise_for_status()
    data = resp.json()

    lines = []
    for body in data.get("body", []):
        content = body.get("content", "").strip()
        if content:
            lines.append(content)
    text = "\n".join(lines)

    out_path = output_dir / "subtitle.txt"
    out_path.write_text(text, encoding="utf-8")
    return out_path


def get_audio_url(view_info: dict, page: dict, referer: str) -> str:
    """Get the best DASH audio stream URL via the playurl API."""
    resp = requests.get(
        PLAYURL_API,
        params={
            "bvid": view_info["bvid"],
            "cid": page["cid"],
            "fnval": 16,
            "qn": 64,
        },
        headers=build_headers(referer),
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Playurl API error: {data.get('code')} {data.get('message')}")

    audio_list = data.get("data", {}).get("dash", {}).get("audio", [])
    if not audio_list:
        raise RuntimeError("No audio stream available")
    # Prefer the highest quality audio entry
    audio_list.sort(key=lambda a: a.get("id", 0), reverse=True)
    return audio_list[0]["baseUrl"]


def download_file(url: str, output_path: Path, referer: str) -> Path:
    """Stream-download a file with the correct Referer header."""
    resp = requests.get(url, headers=build_headers(referer), stream=True, timeout=60)
    resp.raise_for_status()
    tmp = output_path.with_suffix(output_path.suffix + ".part")
    with open(tmp, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
    tmp.replace(output_path)
    return output_path


def download_with_ytdlp(url: str, output_dir: Path, page: dict) -> Path:
    """Fallback: download bestaudio via yt-dlp with retries."""
    audio_path = output_dir / "audio.m4a"
    cmd = [
        "yt-dlp",
        "-f", "bestaudio/best",
        "-o", str(output_dir / "audio.%(ext)s"),
        "--retries", "8",
        "--fragment-retries", "8",
        "--no-playlist",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "yt-dlp failed")
    except FileNotFoundError:
        raise RuntimeError("yt-dlp not found. Install with: pip install yt-dlp")

    found = list(output_dir.glob("audio.*"))
    for f in found:
        if f.suffix.lower() not in (".m4a", ".mp4", ".webm", ".mka"):
            f.unlink()
    if not audio_path.exists():
        candidates = [f for f in output_dir.glob("audio.*") if f.suffix != ".part"]
        if not candidates:
            raise RuntimeError("yt-dlp produced no audio file")
        audio_path = candidates[0]
    return audio_path


def download(url: str, output_dir: Path, p: int = 1, allow_ytdlp: bool = True) -> dict:
    """Download one part. Returns a dict describing what was produced."""
    output_dir.mkdir(parents=True, exist_ok=True)

    bvid, url_p = parse_url(url)
    p = p or url_p

    print(f"Fetching metadata for {bvid} ...")
    view_info = get_view_info(bvid, url)
    page = select_page(view_info, p)

    meta_path = output_dir / "metadata.json"
    meta_path.write_text(
        json.dumps(
            {
                "bvid": view_info.get("bvid", bvid),
                "aid": view_info.get("aid"),
                "title": view_info.get("title", ""),
                "desc": view_info.get("desc", ""),
                "uploader": view_info.get("owner", {}).get("name", ""),
                "uploader_mid": view_info.get("owner", {}).get("mid"),
                "pubdate": view_info.get("pubdate"),
                "tags": view_info.get("tname", ""),
                "stat": view_info.get("stat", {}),
                "pages_count": len(view_info.get("pages", [])),
                "page_index": page.get("page"),
                "part_title": page.get("part", ""),
                "cid": page.get("cid"),
                "duration": page.get("duration", 0),
                "video_url": url,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    total_pages = len(view_info.get("pages", []))
    print(f"\nTitle: {view_info.get('title', '')}")
    print(f"Part: {page.get('page')}/{total_pages} - {page.get('part', '')}")

    # Try subtitle fast-path first
    subtitles = get_subtitles(view_info, page, url)
    if subtitles:
        lan_doc = subtitles[0].get("lan_doc", subtitles[0].get("lan", ""))
        print(f"Found AI subtitles ({lan_doc}), downloading...")
        sub_path = download_subtitle(subtitles[0], output_dir, url)
        print(f"Saved subtitles: {sub_path}")
        return {
            "type": "subtitle",
            "subtitle_path": str(sub_path),
            "metadata_path": str(meta_path),
            "page": page,
        }

    # No subtitles: download audio
    print("No subtitles, downloading audio stream...")
    try:
        audio_url = get_audio_url(view_info, page, url)
        audio_path = download_file(audio_url, output_dir / "audio.m4a", url)
        print(f"Downloaded audio: {audio_path} ({audio_path.stat().st_size} bytes)")
        return {
            "type": "audio",
            "audio_path": str(audio_path),
            "metadata_path": str(meta_path),
            "page": page,
        }
    except Exception as e:
        print(f"Direct audio download failed: {e}")
        if not allow_ytdlp:
            raise
        print("Falling back to yt-dlp...")
        audio_path = download_with_ytdlp(url, output_dir, page)
        print(f"Downloaded audio via yt-dlp: {audio_path}")
        return {
            "type": "audio",
            "audio_path": str(audio_path),
            "metadata_path": str(meta_path),
            "page": page,
        }


def main():
    parser = argparse.ArgumentParser(description="Download Bilibili video (single part)")
    parser.add_argument("url", help="Bilibili video URL, e.g. https://www.bilibili.com/video/BV1xxxx")
    parser.add_argument("-p", "--page", type=int, default=0, help="Part number (default: from URL or 1)")
    parser.add_argument("-o", "--output", default="bilibili_output", help="Output directory")
    parser.add_argument("--no-ytdlp", action="store_true", help="Disable yt-dlp fallback")
    args = parser.parse_args()

    try:
        result = download(args.url, Path(args.output), p=args.page, allow_ytdlp=not args.no_ytdlp)
        print(f"\nDone: {result['type']}")
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
