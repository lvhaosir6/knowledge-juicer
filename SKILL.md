---
name: douyin-summarizer
description: 'Download Douyin (TikTok China) and Bilibili videos, transcribe audio to text using FunASR, and generate structured summaries. Use when user provides a Douyin video URL, a Bilibili video URL, or asks to summarize a video from either platform.'
license: MIT
allowed-tools: Bash, Read, Write
---

# Video Summarizer (Douyin + Bilibili)

Download Douyin/Bilibili videos, extract audio, transcribe to text, and generate structured summaries.

## Prerequisites

Before using this skill, ensure the following tools are installed:

```bash
# 1. Selenium + Chrome WebDriver (video download)
pip install selenium webdriver-manager

# 2. ffmpeg (audio extraction)
# Windows: download from https://ffmpeg.org/download.html
# Or via chocolatey:
choco install ffmpeg

# 3. FunASR (speech recognition)
pip install funasr modelscope torch torchaudio
```

**Note:** yt-dlp alone no longer works for Douyin due to cookie requirements. Selenium is used to bypass this limitation.

## Workflow

### Step 1: Download Video

Douyin requires cookies/authentication to download videos. Use the Selenium-based downloader:

```bash
# Download video using Selenium (handles cookies automatically)
python scripts/download_douyin_selenium.py "<DOUYIN_URL>"
```

This script will:
- Launch a headless Chrome browser
- Navigate to the Douyin video page
- Intercept video URLs from network requests
- Download the video to `douyin_output/video.mp4`

**Alternative methods (if Selenium fails):**
```bash
# Get cookies first, then use yt-dlp
python scripts/get_douyin_cookies.py "<DOUYIN_URL>"
yt-dlp --cookies cookies.txt -o "douyin_output/video.mp4" "<DOUYIN_URL>"
```

### Step 2: Extract Audio

```bash
# Extract audio as WAV (16kHz mono for ASR)
ffmpeg -i "douyin_output/video.mp4" -vn -acodec pcm_s16le -ar 16000 -ac 1 "douyin_output/audio.wav"
```

### Step 3: Transcribe with FunASR

Use the provided `scripts/transcribe.py` script or run directly:

```python
from funasr import AutoModel

# Load model (first run will download ~1GB)
model = AutoModel(
    model="paraformer-zh",
    vad_model="fsmn-vad",
    punc_model="ct-punc",
    device="cpu"  # Use "cuda" if GPU available
)

# Transcribe
result = model.generate(input="douyin_output/audio.wav")
text = result[0]["text"]
print(text)
```

**Model options:**
| Model | Description | Speed |
|-------|-------------|-------|
| `paraformer-zh` | Chinese ASR, best quality | Moderate |
| `paraformer-zh-streaming` | Streaming ASR | Fast |
| `SenseVoiceSmall` | Multi-language, fast | Fast |

### Step 4: Generate Summary

Use the LLM to create a structured summary. Format the prompt:

```
请对以下抖音视频内容进行总结提炼：

【视频转录文本】
{text}

请按以下格式输出：
1. 一句话总结
2. 核心要点（3-5个）
3. 关键信息提取
4. 适用场景/受众
```

## Complete Pipeline Script

Use `scripts/summarize_douyin.py` for the full pipeline (Note: download step needs to be run separately with Selenium):

```bash
# Step 1: Download video with Selenium
python scripts/download_douyin_selenium.py "<DOUYIN_URL>"

# Step 2: Run the rest of the pipeline (extract audio, transcribe, generate summary prompt)
python scripts/summarize_douyin.py "<DOUYIN_URL>" --skip-download
```

## Bilibili Workflow

Bilibili supports **single-part download + summarization**. Direct API calls are used to bypass yt-dlp's intermittent HTTP 412 anti-crawler errors.

### Step 1: Summarize a Bilibili video

```bash
# Default: first part
python scripts/summarize_bilibili.py "https://www.bilibili.com/video/BV1U9iEBREWt"

# Specific part in a multi-part anthology
python scripts/summarize_bilibili.py "https://www.bilibili.com/video/BV1U9iEBREWt" --p 15
```

### How it works

1. **Metadata**: `api.bilibili.com/x/web-interface/view` (no auth) → title, part list, uploader, tags, stats
2. **Subtitle fast-path**: `x/player/wbi/v2` → if AI subtitles exist, download them as text and **skip audio + ASR**
3. **Audio download**: if no subtitles → `x/player/playurl` DASH audio stream (with Referer header), fallback to yt-dlp
4. **Transcribe + summarize**: reuse FunASR/SenseVoiceSmall, then generate structured summary

### LLM auto-summary

Configure `.env` (copy from `.env.example`) to auto-generate `summary.md`:

```
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

If no `LLM_API_KEY`, the script still produces `summary_prompt.md` for any AI to use. CLI args `--llm-api-key` / `--llm-base-url` / `--llm-model` override `.env`.

### Bilibili output structure

```
output/bili_<BV>_p<N>_<timestamp>/
├── metadata.json
├── subtitle.txt          # AI subtitles (if available)
├── audio.m4a             # audio stream (if no subtitles)
├── audio.wav
├── transcript.txt
├── summary_prompt.md
├── summary.md            # LLM summary (if .env configured)
└── pipeline_metadata.json
```

## Output Structure

```
douyin_output/
├── video.mp4          # Original video
├── audio.wav          # Extracted audio
├── transcript.txt     # Raw transcript
├── transcript.json    # Transcript with timestamps
└── summary.md         # Generated summary
```

## Error Handling

| Error | Solution |
|-------|----------|
| `selenium` or `webdriver_manager` not installed | Run `pip install selenium webdriver-manager` |
| `ffmpeg: command not found` | Install ffmpeg from ffmpeg.org |
| `ModuleNotFoundError: funasr` | Run `pip install funasr modelscope torch torchaudio` |
| CUDA out of memory | Use `device="cpu"` or reduce batch size |
| Download fails with cookies error | Run `python scripts/get_douyin_cookies.py` first |
| Chrome driver issues | Run `pip install --upgrade webdriver-manager` |

## Tips

1. **Batch processing**: Create a file with URLs (one per line) and use:
   ```bash
   while read url; do 
     python scripts/download_douyin_selenium.py "$url"
     python scripts/summarize_douyin.py "$url" --skip-download
   done < urls.txt
   ```

2. **GPU acceleration**: If you have NVIDIA GPU:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

3. **Long videos**: For videos > 10 minutes, FunASR automatically handles segmentation via VAD model.

4. **Chrome browser required**: Selenium requires Chrome browser to be installed on the system.

5. **Troubleshooting downloads**: If Selenium download fails, try:
   - Update Chrome browser to latest version
   - Run `pip install --upgrade selenium webdriver-manager`
   - Check if the video is publicly accessible
