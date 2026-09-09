---
name: generate-questions
description: 'Generate interview questions and knowledge-point questions from course video transcripts and AI summaries. Use when the user wants 面试常见问题 (interview questions for recitation) or 知识点问题 (knowledge consolidation questions) based on Bilibili/Douyin course content already summarized in output/.'
license: MIT
allowed-tools: Read, Write, Glob
---

# Course Question Generator

从已总结的课程视频（转录文本 + AI 总结）生成两类题目：
- `interview_questions.md` — 面试官视角常见问题，用于背诵，回答必须口语化
- `knowledge_questions.md` — 知识点巩固题（简答 + 选择混合），用于自测

## 触发方式

本技能位于项目内（`generate_questions/SKILL.md`），不会自动注册到 Agent 技能列表。触发时需在指令中明确指定：

- **下载 + 转录 + 出题**：`下载并处理课程第N集，并按 generate_questions 技能生成面试题和知识点题。https://www.bilibili.com/video/BV1U9iEBREWt`
- **只转录不出题**：`下载并处理课程第N集。https://www.bilibili.com/video/BV1U9iEBREWt`
- **对已转录的集补出题**：`对 output/bili_<BV>_p<N>_<timestamp>/ 按 generate_questions 技能生成题目`

指令中带有"按 generate_questions 技能出题"时，才读取本文件并按其工作流执行。

## 输入定位

1. 定位课程集目录：`output/bili_<BV>_p<N>_<timestamp>/`（每集一个目录）
2. 读取两个输入文件：
   - `transcript.txt`（视频转录文本，必需）
   - `summary.md`（AI 总结，可选，有则作为辅助）

## 输出

在与输入相同的集目录下写两个文件：
- `interview_questions.md`
- `knowledge_questions.md`

## 工作流

1. 读取 `transcript.txt`（和 `summary.md`）
2. 判断该集是否有实质教学内容：
   - 有 → 按下方提示词生成两套题目
   - 无（纯课程介绍/广告/闲聊）→ 跳过，输出说明
3. 将结果写入同目录两个文件
4. 若处理完所有集，生成 `output/questions_index.md` 汇总索引

## 面试题生成提示词

```
你是一名软件测试领域的资深面试官，正在为一位学习课程《软件测试零基础入门到精通》的求职者出面试题。

【课程信息】
课时：{part_title}
视频标题：{video_title}

【视频转录文本】
{transcript}

【AI总结（辅助参考）】
{summary}

请基于以上课程内容，站在面试官视角生成 3-5 道常见面试题。

要求：
1. 题目必须是面试官会真实问出口的问题，聚焦课程讲到的技术点，不要脱离课程内容编造
2. 标注面试频度：🔴 高频 / 🟡 中频 / ⚪ 低频
3. 每题提供"参考回答"，参考回答必须口语化——像求职者张嘴说出来一样，用"一般我会…"、"首先…然后…"这样的自然口语，不要书面语、不要列表堆砌
4. 每题末尾标注"出自：该知识点对应的课程内容"
5. 按频度分组：先高频，再中频，最后低频

输出格式：

# {part_title} - 面试常见问题

## 高频题

### Q1. {题目}
- 频度：🔴 高频
- 参考回答（口语化）：
  {口语化回答，1-3 句或一段话，像真的在说话}
- 出自：{关联的课程知识点}

## 中频题
（同上格式）

## 低频题
（同上格式）
```

## 知识点题生成提示词

```
你是一名软件测试课程的助教，正在为学生制作知识点巩固练习题。

【课程信息】
课时：{part_title}
视频标题：{video_title}

【视频转录文本】
{transcript}

【AI总结（辅助参考）】
{summary}

请基于以上课程内容生成 5-8 道知识点题，题型混合：
- 简答题 2-4 道：开放式问题，需要学生用自己的话回答，每题附参考答案
- 选择题 3-4 道：单选，每题 4 个选项，附答案和一句解析

要求：
1. 所有题目必须来自课程实际讲到的内容，课程没讲的不要编造
2. 选择题选项要合理，干扰项要有迷惑性
3. 简答题参考答案要准确、完整但精炼
4. 若该集为纯介绍/广告内容（没有实质知识点），跳过并说明"本集无实质知识点内容"

输出格式：

# {part_title} - 知识点巩固

## 简答题

### 1. {题目}
答：{参考答案}

## 选择题

### 2. {题干}
A. {选项}
B. {选项}
C. {选项}
D. {选项}
答案：{A/B/C/D}
解析：{一句解析}
```

## 汇总索引格式

当所有集处理完成后，生成 `output/questions_index.md`：

```markdown
# 课程面试题与知识点题索引

## 章节：{篇章/课时}
- {课时名}：[面试题]({目录}/interview_questions.md) | [知识点题]({目录}/knowledge_questions.md)
```

## 注意事项

- 口语化是硬要求：参考回答读出来要像人话，避免"综上所述"、"具体而言"等书面腔
- 宁缺毋滥：内容少的集就少出题，不要硬凑
- 忠于课程：题目和答案都要能追溯到课程原文
