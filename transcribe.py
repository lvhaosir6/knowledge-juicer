from funasr import AutoModel

model = AutoModel(
    model="paraformer-zh",
    vad_model="fsmn-vad",
    punc_model="ct-punc",
    device="cpu",
    disable_update=True,
)

res = model.generate(input="output/audio.wav", batch_size_s=300, return_spk_res=False)
text = res[0]["text"]
with open("output/transcript.txt", "w", encoding="utf-8") as f:
    f.write(text)
print("LENGTH:", len(text))
print(text[:2000])
