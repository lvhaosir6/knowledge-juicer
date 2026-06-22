# 🎬 Douyin Video Summarizer

> 抖音视频一键转文字 + AI总结 | 全免费 | 本地运行 | 隐私安全

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

**无需付费API | 无需云端服务 | 完全本地运行 | 保护你的隐私**

---

## ✨ 为什么选择这个工具？

| 特点 | 说明 |
|------|------|
| 🆓 **完全免费** | 不需要任何付费API，所有组件开源 |
| 🔒 **本地运行** | 视频、音频、文本都在本地处理，隐私安全 |
| 🇨🇳 **中文优化** | 使用SenseVoiceSmall模型，中文识别效果优秀 |
| ⚡ **简单高效** | 一行命令，自动完成下载→转录→总结 |
| 🎯 **结构化输出** | 自动生成总结提示词，直接发给AI即可 |
| 🤖 **Agent集成** | 可作为Skill加载到ClaudeCode、OpenCode等AI Agent |
| 🔌 **可扩展** | 基于yt-dlp，支持扩展到其他视频平台 |

## 📺 支持平台

| 平台 | 状态 | 说明 |
|------|------|------|
| 🎵 抖音 | ✅ 已支持 | 完整支持，包括图文、视频 |
| 📺 B站 | 🔄 计划中 | |
| 📹 YouTube | 🔄 计划中 | |
| 🎬 快手 | 🔄 计划中 | |
| 📱 小红书 | 🔄 计划中 | |
| 🎤 微信视频号 | 🔄 计划中 | |

> 💡 本工具基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp)，理论上支持 yt-dlp 所有平台。欢迎提交 PR 扩展更多平台！

## 🚀 安装方式

### 方式一：作为 Agent Skill 安装（推荐）

将此项目作为 Skill 加载到你的 AI Agent 中，即可通过自然语言调用。

**ClaudeCode / OpenCode:**

```bash
# 克隆到 skills 目录
git clone https://github.com/your-username/douyin-summarizer.git ~/.agents/skills/douyin-summarizer
```

**或者复制现有项目：**
```bash
# 如果你已经有这个项目
cp -r /path/to/douyin-summarizer ~/.agents/skills/
```

安装后，在 Agent 中直接使用：
```
用户: 帮我总结这个抖音视频 https://v.douyin.com/xxxxx
Agent: [自动调用 douyin-summarizer skill 执行下载、转录、总结]
```

**支持的 Agent：**

| Agent | Skill 目录 | 说明 |
|-------|-----------|------|
| ClaudeCode | `~/.agents/skills/` 或 `~/.claude/skills/` | Anthropic 官方 CLI |
| OpenCode | `~/.agents/skills/` | 开源 AI 编程助手 |
| Cursor | `.cursorrules` 或项目内 | AI 代码编辑器 |
| Windsurf | 项目内 `.windsurfrules` | Codeium 编辑器 |

### 方式二：Python 脚本直接使用

```bash
# 克隆项目
git clone https://github.com/your-username/douyin-summarizer.git
cd douyin-summarizer

# 安装依赖
pip install -r requirements.txt

# 安装 ffmpeg
# Windows: choco install ffmpeg
# macOS: brew install ffmpeg
# Linux: apt install ffmpeg
```

### 下载模型（约1GB）

```bash
# 国内用户推荐 ModelScope
pip install modelscope
python -c "from modelscope import snapshot_download; snapshot_download('iic/SenseVoiceSmall', local_dir='./SenseVoiceSmall')"

# 或者使用 HuggingFace
pip install huggingface_hub
python -c "from huggingface_hub import snapshot_download; snapshot_download('FunAudioLLM/SenseVoiceSmall', local_dir='./SenseVoiceSmall')"
```

## 📖 使用方法

### 在 Agent 中使用（Skill 模式）

安装为 Skill 后，直接用自然语言与 Agent 对话：

```
# 单个视频总结
"帮我总结这个抖音视频 https://v.douyin.com/xxxxx"

# 批量处理
"帮我总结这几个抖音视频：
- https://v.douyin.com/aaa
- https://v.douyin.com/bbb
- https://v.douyin.com/ccc"

# 指定输出目录
"把视频总结保存到 study_notes 目录"
```

### 命令行使用（脚本模式）

```bash
# 基本用法
python scripts/summarize_douyin.py "https://v.douyin.com/xxxxx"

# 指定输出目录
python scripts/summarize_douyin.py "https://v.douyin.com/xxxxx" -o my_output

# 使用GPU加速
python scripts/summarize_douyin.py "https://v.douyin.com/xxxxx" --device cuda

# 跳过下载，使用已有音频
python scripts/summarize_douyin.py "https://v.douyin.com/xxxxx" --audio-only ./audio.wav
```

## 📁 输出结构

```
output/20260613_115055/
├── video.mp4           # 下载的视频
├── audio.wav           # 提取的音频
├── transcript.txt      # 转录文本
├── summary_prompt.md   # 总结提示词（复制给AI即可）
└── pipeline_metadata.json
```

## 🔧 参数说明

```bash
python scripts/summarize_douyin.py [URL] [OPTIONS]

Options:
  -o, --output DIR      输出目录 (默认: output/YYYYMMDD_HHmmss)
  -m, --model MODEL     模型路径 (默认: ./SenseVoiceSmall)
  -d, --device DEVICE   设备: cpu/cuda (默认: cpu)
  --skip-download       跳过下载步骤
  --audio-only FILE     直接使用已有音频文件
```

## 💡 应用场景

- 📚 **学习笔记** - 快速提取视频课程核心内容
- 📰 **资讯整理** - 批量总结新闻、资讯视频
- 🎓 **知识管理** - 建立个人知识库
- 📊 **竞品分析** - 分析同行视频内容
- 🔍 **内容研究** - 提取视频关键信息
- 🤖 **AI 工作流** - 集成到 Agent 自动化处理

## 🛠️ 技术栈

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 视频下载
- [FFmpeg](https://ffmpeg.org/) - 音频处理
- [FunASR](https://github.com/modelscope/FunASR) - 语音识别
- [SenseVoiceSmall](https://github.com/FunAudioLLM/SenseVoice) - ASR模型

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建你的分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源 - 详见 [LICENSE](LICENSE) 文件

## ⭐ 支持

如果这个项目对你有帮助，请给个 Star ⭐ 支持一下！

## ❓ 常见问题

**Q: 下载失败？**
A: 确保视频是公开的，URL格式正确。可尝试更新yt-dlp: `pip install -U yt-dlp`

**Q: GPU加速？**
A: 安装CUDA版本的PyTorch后使用 `--device cuda` 参数

**Q: 内存不足？**
A: 使用CPU模式即可

**Q: 模型下载慢？**
A: 使用 ModelScope 国内源

**Q: 如何在 Agent 中使用？**
A: 克隆到 `~/.agents/skills/` 目录，重启 Agent 即可自动加载

---

**Made with ❤️ for the Chinese content creator community**
