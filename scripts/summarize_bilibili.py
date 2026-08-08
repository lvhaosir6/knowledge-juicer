#!/usr/bin/env python3
"""
Bilibili Video Summarizer - Complete Pipeline
Downloads a single part (audio or AI subtitles), transcribes it, and generates
a structured summary. Summary is produced by calling an LLM (configured in
.env) or by saving a summary prompt for the current agent to finish.

Output directory:
  output/bili_<BV>_p<N>_<YYYYMMDD_HHMMSS>/
    metadata.json      - video metadata
    subtitle.txt       - AI subtitles (if available)
    audio.m4a          - audio stream (if no subtitles)
    audio.wav          - extracted audio
    transcript.txt     - raw transcript
    summary_prompt.md  - summary prompt (always)
    summary.md         - final summary (only if LLM configured)
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(SCRIPT_DIR))

import download_bilibili  # noqa: E402
import llm_config  # noqa: E402
from transcribe import resolve_model_path, transcribe  # noqa: E402


def run_command(cmd: list, description: str) -> bool:
    """Run a shell command and return success status."""
    print(f"\n{'='*50}")
    print(f"Step: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*50)
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(e.stderr)
        return False
    except FileNotFoundError:
        print(f"Command not found: {cmd[0]}")
        return False


def extract_audio(video_path: Path, output_dir: Path) -> Path:
    """Extract audio as 16kHz mono WAV using ffmpeg."""
    audio_path = output_dir / "audio.wav"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path),
    ]
    if not run_command(cmd, "Extract audio"):
        return None
    return audio_path


def load_metadata(output_dir: Path) -> dict:
    meta_path = output_dir / "metadata.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def format_stats(metadata: dict) -> str:
    stat = metadata.get("stat", {})
    parts = []
    if stat.get("view"):
        parts.append(f"播放 {stat['view']}")
    if stat.get("danmaku"):
        parts.append(f"弹幕 {stat['danmaku']}")
    if stat.get("like"):
        parts.append(f"点赞 {stat['like']}")
    if stat.get("coin"):
        parts.append(f"投币 {stat['coin']}")
    if stat.get("favorite"):
        parts.append(f"收藏 {stat['favorite']}")
    if stat.get("reply"):
        parts.append(f"评论 {stat['reply']}")
    return "，".join(parts)


def generate_summary_prompt(text: str, metadata: dict) -> str:
    """Build an LLM prompt with rich bilibili context."""
    title = metadata.get("title", "未知标题")
    part_title = metadata.get("part_title", "")
    uploader = metadata.get("uploader", "")
    pages_count = metadata.get("pages_count", 1)
    page_index = metadata.get("page_index", 1)
    description = metadata.get("desc", "")
    tags = metadata.get("tags", "")
    stats = format_stats(metadata)
    duration = metadata.get("duration", 0)
    minutes = int(duration / 60)

    header_parts = [f"标题：{title}"]
    if part_title and part_title != title:
        header_parts.append(f"分P标题（第{page_index}集/{pages_count}集）：{part_title}")
    if uploader:
        header_parts.append(f"UP主：{uploader}")
    if tags:
        header_parts.append(f"标签：{tags}")
    if stats:
        header_parts.append(f"数据：{stats}")
    if minutes:
        header_parts.append(f"时长：约{minutes}分钟")

    prompt = f"""请对以下哔哩哔哩视频内容进行总结提炼：

【视频信息】
{'；'.join(header_parts)}
{f'简介：{description}' if description else ''}

【视频转录文本】
{text}

请按以下格式输出总结：

## 一句话总结
（用一句话概括视频核心内容）

## 核心要点
1. （要点1）
2. （要点2）
3. （要点3）

## 关键信息
- （提取关键数据、观点或方法）

## 适用场景
- （这个视频适合什么人群/场景）

## 关键词
（3-5个关键词，用逗号分隔）"""

    return prompt


def get_default_output_dir(bvid: str, page: int) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"output/bili_{bvid}_p{page}_{timestamp}"


def get_bvid_from_url(url: str) -> str:
    import re

    m = re.search(r"(BV[0-9A-Za-z]{10})", url)
    return m.group(1) if m else "unknown"


def main():
    parser = argparse.ArgumentParser(description="Bilibili Video Summarizer Pipeline")
    parser.add_argument("url", help="Bilibili video URL")
    parser.add_argument("-p", "--page", type=int, default=0, help="Part number (default: from URL or 1)")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: output/bili_BV_pN_timestamp)")
    parser.add_argument("-m", "--model", default=str(PROJECT_ROOT / "SenseVoiceSmall"), help="Path to local SenseVoiceSmall model directory")
    parser.add_argument("-d", "--device", default="cpu", choices=["cpu", "cuda"], help="Device")
    parser.add_argument("--skip-download", action="store_true", help="Skip download step (reuse existing files)")
    parser.add_argument("--audio-only", help="Use existing audio file instead of downloading")
    parser.add_argument("--llm-api-key", default="", help="Overwrite LLM_API_KEY from .env")
    parser.add_argument("--llm-base-url", default="", help="Overwrite LLM_BASE_URL from .env")
    parser.add_argument("--llm-model", default="", help="Overwrite LLM_MODEL from .env")
    parser.add_argument("--no-ytdlp", action="store_true", help="Disable yt-dlp fallback in downloader")

    args = parser.parse_args()
    args.model = resolve_model_path(args.model)

    bvid = get_bvid_from_url(args.url)
    if args.output is None:
        args.output = get_default_output_dir(bvid, args.page or 1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Step 1: obtain text (subtitles or audio) + metadata
    metadata = load_metadata(output_dir)
    text = None
    transcript_path = None

    if args.audio_only:
        audio_path = Path(args.audio_only)
        if not audio_path.exists():
            print(f"Error: Audio file not found: {audio_path}")
            sys.exit(1)
    elif args.skip_download:
        # Reuse files already in the output dir
        audio_path = None
        sub_path = output_dir / "subtitle.txt"
        if sub_path.exists():
            text = sub_path.read_text(encoding="utf-8")
            print(f"Reusing subtitles: {sub_path}")
        else:
            # Prefer an existing wav (skip re-extraction), then any audio source
            wav = output_dir / "audio.wav"
            if wav.exists():
                audio_path = wav
            else:
                candidates = [p for p in output_dir.glob("audio.*") if p.name != "audio.wav"]
                if not candidates:
                    print("Error: No audio or subtitle found in output directory (--skip-download)")
                    sys.exit(1)
                audio_path = candidates[0]
        if not metadata:
            metadata = load_metadata(output_dir)
    else:
        result = download_bilibili.download(
            args.url, output_dir, p=args.page, allow_ytdlp=not args.no_ytdlp
        )
        metadata = load_metadata(output_dir)
        if result["type"] == "subtitle":
            text = Path(result["subtitle_path"]).read_text(encoding="utf-8")
        else:
            audio_path = Path(result["audio_path"])

    # Step 2: extract audio and transcribe if we have audio
    if text is None and audio_path is not None:
        if audio_path.suffix.lower() == ".wav":
            wav_path = audio_path
        else:
            wav_path = extract_audio(audio_path, output_dir)
        if not wav_path:
            print("Failed to extract audio")
            sys.exit(1)

        transcript = transcribe(str(wav_path), args.model, args.device)
        if not transcript or not transcript["text"]:
            print("Failed to transcribe audio")
            sys.exit(1)
        text = transcript["text"]
        transcript_path = output_dir / "transcript.txt"
        transcript_path.write_text(text, encoding="utf-8")
        print(f"Saved transcript: {transcript_path}")

    if not text or not text.strip():
        print("Error: No transcript/subtitle content obtained")
        sys.exit(1)

    if transcript_path is None:
        transcript_path = output_dir / "transcript.txt"
        transcript_path.write_text(text, encoding="utf-8")
        print(f"Saved transcript: {transcript_path}")

    # Step 3: generate summary prompt (always)
    prompt = generate_summary_prompt(text, metadata)
    prompt_path = output_dir / "summary_prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    print(f"\nSummary prompt saved: {prompt_path}")

    # Step 4: generate final summary with LLM if configured
    config = llm_config.get_config(
        api_key=args.llm_api_key, base_url=args.llm_base_url, model=args.llm_model
    )
    summary_path = None
    if llm_config.is_configured(config):
        print(f"\nCalling LLM ({config['model']}) ...")
        try:
            summary = llm_config.generate_summary(prompt, config)
            summary_path = output_dir / "summary.md"
            summary_path.write_text(summary, encoding="utf-8")
            print(f"Summary saved: {summary_path}")
        except Exception as e:
            print(f"LLM call failed: {e}")
            llm_config.print_config_hint()
    else:
        llm_config.print_config_hint()

    # Step 5: pipeline metadata
    pipeline_meta = {
        "url": args.url,
        "page": args.page or 1,
        "timestamp": datetime.now().isoformat(),
        "model": args.model,
        "device": args.device,
        "video_title": metadata.get("title", ""),
        "part_title": metadata.get("part_title", ""),
        "transcript_length": len(text),
        "summary_generated": summary_path is not None,
    }
    meta_path = output_dir / "pipeline_metadata.json"
    meta_path.write_text(json.dumps(pipeline_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*50}")
    print("Pipeline complete!")
    print(f"Output directory: {output_dir}")
    print(f"Transcript: {transcript_path}")
    print(f"Summary prompt: {prompt_path}")
    if summary_path:
        print(f"Summary: {summary_path}")
    print('='*50)


if __name__ == "__main__":
    main()
