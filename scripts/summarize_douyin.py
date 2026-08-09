#!/usr/bin/env python3
"""
Douyin Video Summarizer - Complete Pipeline
Downloads video, extracts audio, transcribes, and generates summary.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL = str(PROJECT_ROOT / "SenseVoiceSmall")
DEFAULT_VAD_MODEL = str(PROJECT_ROOT / "models" / "speech_fsmn_vad_zh-cn-16k-common-pytorch")

sys.path.insert(0, str(SCRIPT_DIR))

import llm_config  # noqa: E402


def resolve_model_path(model: str) -> str:
    """Resolve relative model path against project root."""
    p = Path(model)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return str(p)


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
        print("Please ensure the required tools are installed.")
        return False


def download_video(url: str, output_dir: Path, cookie_file: str = "cookies.txt") -> Path:
    """Download Douyin video using yt-dlp."""
    output_template = str(output_dir / "%(title)s.%(ext)s")
    
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-o", output_template,
        "--write-info-json",
    ]
    
    # Use cookies if available (Douyin requires fresh cookies)
    if Path(cookie_file).exists():
        cmd += ["--cookies", cookie_file]
    
    cmd.append(url)
    
    if not run_command(cmd, "Download Douyin video"):
        return None
    
    # Find the downloaded video file
    video_files = list(output_dir.glob("*.mp4")) + list(output_dir.glob("*.webm"))
    if not video_files:
        print("Error: No video file found after download")
        return None
    
    return video_files[0]


def extract_audio(video_path: Path, output_dir: Path) -> Path:
    """Extract audio from video using ffmpeg."""
    audio_path = output_dir / "audio.wav"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path)
    ]
    
    if not run_command(cmd, "Extract audio"):
        return None
    
    return audio_path


def transcribe_audio(audio_path: Path, output_dir: Path, model: str = "./SenseVoiceSmall", device: str = "cpu") -> dict:
    """Transcribe audio using FunASR SenseVoiceSmall."""
    try:
        from funasr import AutoModel
        from funasr.utils.postprocess_utils import rich_transcription_postprocess
    except ImportError:
        print("Error: funasr not installed. Run: pip install funasr modelscope torch torchaudio")
        return None
    
    print(f"\n{'='*50}")
    print(f"Step: Transcribe audio")
    print(f"Model: {model}, Device: {device}")
    print('='*50)
    
    print("Loading model...")
    asr_model = AutoModel(
        model=model,
        vad_model=DEFAULT_VAD_MODEL,
        vad_kwargs={"max_single_segment_time": 30000},
        device=device,
        hub="ms",
        disable_update=True,
    )
    
    print("Transcribing...")
    result = asr_model.generate(
        input=str(audio_path),
        cache={},
        language="auto",  # "zn", "en", "yue", "ja", "ko", "nospeech"
        use_itn=True,
        batch_size_s=60,
        merge_vad=True,
        merge_length_s=15,
    )
    
    if not result:
        return None
    
    # Post-process the text
    text = rich_transcription_postprocess(result[0]["text"])
    
    # Save transcript
    transcript_path = output_dir / "transcript.txt"
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Saved transcript: {transcript_path}")
    
    return {"text": text, "path": str(transcript_path)}


def load_metadata(output_dir: Path) -> dict:
    """Load video metadata if available."""
    json_files = list(output_dir.glob("*.info.json"))
    if json_files:
        with open(json_files[0], "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def generate_summary_prompt(text: str, metadata: dict) -> str:
    """Generate prompt for LLM summary."""
    title = metadata.get("title", "未知标题")
    description = metadata.get("description", "")
    
    prompt = f"""请对以下抖音视频内容进行总结提炼：

【视频信息】
标题：{title}
{f"描述：{description}" if description else ""}

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


def get_default_output_dir() -> str:
    """Generate default output directory name with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"output/{timestamp}"


def main():
    parser = argparse.ArgumentParser(description="Douyin Video Summarizer Pipeline")
    parser.add_argument("url", help="Douyin video URL")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: output/YYYYMMDD_HHmmss)")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help="Path to local SenseVoiceSmall model directory")
    parser.add_argument("-d", "--device", default="cpu", choices=["cpu", "cuda"], help="Device")
    parser.add_argument("--skip-download", action="store_true", help="Skip download step")
    parser.add_argument("--audio-only", help="Use existing audio file instead of downloading")
    parser.add_argument("--llm-api-key", default="", help="Overwrite LLM_API_KEY from .env")
    parser.add_argument("--llm-base-url", default="", help="Overwrite LLM_BASE_URL from .env")
    parser.add_argument("--llm-model", default="", help="Overwrite LLM_MODEL from .env")
    
    args = parser.parse_args()
    args.model = resolve_model_path(args.model)
    
    # Use default output directory if not specified
    if args.output is None:
        args.output = get_default_output_dir()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Output directory: {output_dir}")
    
    # Step 1: Download video
    if args.audio_only:
        audio_path = Path(args.audio_only)
        if not audio_path.exists():
            print(f"Error: Audio file not found: {audio_path}")
            sys.exit(1)
        metadata = {}
    else:
        if not args.skip_download:
            video_path = download_video(args.url, output_dir)
            if not video_path:
                print("Failed to download video")
                sys.exit(1)
            print(f"Downloaded: {video_path}")
        
        metadata = load_metadata(output_dir)
        
        # Step 2: Extract audio
        video_files = list(output_dir.glob("*.mp4")) + list(output_dir.glob("*.webm"))
        if not video_files:
            print("Error: No video file found in output directory")
            sys.exit(1)
        
        audio_path = extract_audio(video_files[0], output_dir)
        if not audio_path:
            print("Failed to extract audio")
            sys.exit(1)
        print(f"Audio extracted: {audio_path}")
    
    # Step 3: Transcribe
    transcript = transcribe_audio(audio_path, output_dir, args.model, args.device)
    if not transcript:
        print("Failed to transcribe audio")
        sys.exit(1)
    
    # Step 4: Generate summary prompt
    prompt = generate_summary_prompt(transcript["text"], metadata)
    
    # Save prompt for LLM
    prompt_path = output_dir / "summary_prompt.md"
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"\nSummary prompt saved: {prompt_path}")
    
    # Step 5: Generate final summary with LLM if configured
    config = llm_config.get_config(
        api_key=args.llm_api_key, base_url=args.llm_base_url, model=args.llm_model
    )
    summary_path = None
    if llm_config.is_configured(config):
        print(f"\nCalling LLM ({config['model']}) ...")
        try:
            summary = llm_config.generate_summary(prompt, config)
            summary_path = output_dir / "summary.md"
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(summary)
            print(f"Summary saved: {summary_path}")
        except Exception as e:
            print(f"LLM call failed: {e}")
            llm_config.print_config_hint()
    else:
        llm_config.print_config_hint()
    
    # Save pipeline metadata
    pipeline_meta = {
        "url": args.url,
        "timestamp": datetime.now().isoformat(),
        "model": args.model,
        "device": args.device,
        "video_title": metadata.get("title", ""),
        "transcript_length": len(transcript["text"]),
        "summary_generated": summary_path is not None,
    }
    
    meta_path = output_dir / "pipeline_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(pipeline_meta, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print("Pipeline complete!")
    print(f"Output directory: {output_dir}")
    print(f"Transcript: {transcript['path']}")
    print(f"Summary prompt: {prompt_path}")
    if summary_path:
        print(f"Summary: {summary_path}")
    print('='*50)
    if not summary_path:
        print("\nNext step: Use the summary prompt with an LLM to generate the final summary.")
        print("You can copy the prompt content and paste it to your AI assistant.")


if __name__ == "__main__":
    main()
