import os
d = 'output/20260827_161320'
t = open(os.path.join(d, 'transcript.txt'), encoding='utf-8').read()
prompt = (
    "请对以下抖音视频内容进行总结提炼：\n\n"
    "【视频转录文本】\n" + t + "\n\n"
    "请按以下格式输出：\n"
    "1. 一句话总结\n"
    "2. 核心要点（3-5个）\n"
    "3. 关键信息提取\n"
    "4. 适用场景/受众\n"
)
open(os.path.join(d, 'summary_prompt.md'), 'w', encoding='utf-8').write(prompt)
print('written summary_prompt.md, len', len(prompt))
