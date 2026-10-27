"""Local VI->EN translation for text queries (CPU, no API).
opus: Helsinki-NLP/opus-mt-vi-en (MarianMT, Apache-2.0)  | vinai: vinai/vinai-translate-vi2en-v2 (mBART, AGPL-3.0)."""
import time, torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
class Translator:
    def __init__(self, kind="vinai"):
        self.kind = kind; n = {"opus": "Helsinki-NLP/opus-mt-vi-en", "vinai": "vinai/vinai-translate-vi2en-v2"}[kind]
        self.tok = AutoTokenizer.from_pretrained(n, **({"src_lang": "vi_VN"} if kind == "vinai" else {})); self.m = AutoModelForSeq2SeqLM.from_pretrained(n).eval(); self.cache = {}
    @torch.no_grad()
    def __call__(self, text):
        if text in self.cache: return self.cache[text], 0.0
        t = time.time(); x = self.tok([text], return_tensors="pt", padding=True)
        kw = {"decoder_start_token_id": self.tok.lang_code_to_id["en_XX"]} if self.kind == "vinai" else {}
        out = self.tok.batch_decode(self.m.generate(**x, num_beams=4, max_new_tokens=64, **kw), skip_special_tokens=True)[0]
        ms = (time.time() - t) * 1000; self.cache[text] = out; return out, ms
