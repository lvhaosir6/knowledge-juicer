#!/usr/bin/env python3
"""
Douyin Video Summarizer - Transcription Module
Uses FunASR for speech-to-text conversion.
"""

import argparse
import json
import os
import sys
from pathlib import Path


def check_dependencies():
    """Check if required packages are installed."""
    missing = []
    try:
        import funasr
    except ImportError:
        missing.append("funasr")
    try:
        import torch
    except ImportError:
        missing.append("torch")
    
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)} modelscope torchaudio")
        sys.exit(1)


def transcribe(audio_path: str, model_path: str = "./SenseVoiceSmall", device: str = "cpu") -> dict:
    """
    Transcribe audio file to text using FunASR SenseVoiceSmall.
    
    Args:
        audio_path: Path to audio file (WAV format recommended)
        model_path: Path to local SenseVoiceSmall model directory
        device: "cpu" or "cuda" for GPU
    
    Returns:
        dict with "text" and "sentences" keys
    """
    from funasr import AutoModel
    from funasr.utils.postprocess_utils import rich_transcription_postprocess
    
    print(f"Loading model from: {model_path}...")
    model = AutoModel(
        model=model_path,
        vad_model="fsmn-vad",
        vad_kwargs={"max_single_segment_time": 30000},
        device=device,
        hub="hf",
    )
    
    print(f"Transcribing: {audio_path}")
    result = model.generate(
        input=audio_path,
        cache={},
        language="auto",  # "zn", "en", "yue", "ja", "ko", "nospeech"
        use_itn=True,
        batch_size_s=60,
        merge_vad=True,
        merge_length_s=15,
    )
    
    if not result:
        return {"text": "", "sentences": []}
    
    # Post-process the text
    text = rich_transcription_postprocess(result[0]["text"])
    
    # Try to get sentence-level timestamps if available
    sentences = []
    if "sentence_info" in result[0]:
        for sent in result[0]["sentence_info"]:
            sentences.append({
                "text": sent.get("text", ""),
                "start": sent.get("start", 0),
                "end": sent.get("end", 0)
            })
    
    return {"text": text, "sentences": sentences}


def save_transcript(result: dict, output_path: str):
    """Save transcription result to files."""
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save plain text
    txt_path = Path(output_path).with_suffix(".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])
    print(f"Saved transcript: {txt_path}")
    
    # Save JSON with timestamps
    json_path = Path(output_path).with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON: {json_path}")


def main():
    parser = argparse.ArgumentParser(description="Transcribe audio using FunASR SenseVoiceSmall")
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument("-o", "--output", default=None, help="Output path (default: same as input)")
    parser.add_argument("-m", "--model", default="./SenseVoiceSmall", 
                        help="Path to local SenseVoiceSmall model directory")
    parser.add_argument("-d", "--device", default="cpu", choices=["cpu", "cuda"],
                        help="Device to use (cpu/cuda)")
    
    args = parser.parse_args()
    
    # Check dependencies
    check_dependencies()
    
    # Set default output path
    if args.output is None:
        args.output = str(Path(args.audio).with_suffix(""))
    
    # Transcribe
    result = transcribe(args.audio, args.model, args.device)
    
    # Save results
    save_transcript(result, args.output)
    
    # Print summary
    print(f"\nTranscription complete!")
    print(f"Text length: {len(result['text'])} characters")
    if result['sentences']:
        print(f"Sentences: {len(result['sentences'])}")


if __name__ == "__main__":
    main()
