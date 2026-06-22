---
name: douyin-summarizer
description: 'Download Douyin (TikTok China) videos, transcribe audio to text using FunASR, and generate structured summaries. Use when user provides a Douyin video URL or asks to summarize a Douyin video.'
license: MIT
allowed-tools: Bash, Read, Write
---

# Douyin Video Summarizer

Download Douyin videos, extract audio, transcribe to text, and generate structured summaries.

## Prerequisites

Before using this skill, ensure the following tools are installed:

```bash
# 1. yt-dlp (video download)
pip install yt-dlp

# 2. ffmpeg (audio extraction)
# Windows: download from https://ffmpeg.org/download.html
# Or via chocolatey:
choco install ffmpeg

# 3. FunASR (speech recognition)
pip install funasr modelscope torch torchaudio
```

## Workflow

### Step 1: Download Video

```bash
# Create output directory
mkdir -p douyin_output

# Download video with yt-dlp
yt-dlp -o "douyin_output/%(title)s.%(ext)s" --no-watermark "<DOUYIN_URL>"
```

**Common yt-dlp options for Douyin:**
- `--no-watermark` - Download without watermark
- `-f best` - Best quality
- `--write-info-json` - Save video metadata

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

Use `scripts/summarize_douyin.py` for the full pipeline:

```bash
python scripts/summarize_douyin.py "<DOUYIN_URL>"
```

## Output Structure

```
douyin_output/
├── video.mp4          # Original video
├── audio.wav          # Extracted audio
├── transcript.txt     # Raw transcript
├── summary.md         # Generated summary
└── metadata.json      # Video metadata
```

## Error Handling

| Error | Solution |
|-------|----------|
| `yt-dlp: command not found` | Run `pip install yt-dlp` |
| `ffmpeg: command not found` | Install ffmpeg from ffmpeg.org |
| `ModuleNotFoundError: funasr` | Run `pip install funasr modelscope torch torchaudio` |
| CUDA out of memory | Use `device="cpu"` or reduce batch size |
| Download fails | Check URL format, ensure video is public |

## Tips

1. **Batch processing**: Create a file with URLs (one per line) and use:
   ```bash
   while read url; do python scripts/summarize_douyin.py "$url"; done < urls.txt
   ```

2. **GPU acceleration**: If you have NVIDIA GPU:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

3. **Long videos**: For videos > 10 minutes, FunASR automatically handles segmentation via VAD model.

4. **Quality**: Use `--write-info-json` to preserve original video title and description for context.
