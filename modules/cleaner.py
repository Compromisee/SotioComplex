import re, html
from rapidfuzz import fuzz

class TextCleaner:
    @staticmethod
    def clean(text):
        if not text: return ""
        text = html.unescape(text)
        text = re.sub(r'\\[ntr"\']', ' ', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        for j in ['Subscribe','Sign up','Cookie','Privacy Policy','Advertisement','Newsletter','©']:
            text = re.sub(j, '', text, flags=re.I)
        return text.strip()
    @staticmethod
    def dedupe_paragraphs(text):
        paras = [p.strip() for p in text.split('\n') if p.strip()]
        unique = []
        for p in paras:
            if not any(fuzz.ratio(p,u) > 90 for u in unique): unique.append(p)
        return '\n'.join(unique)
    @staticmethod
    def filter_short(text, min_words=100): return len(text.split()) >= min_words
    @staticmethod
    def has_blacklisted(text, kws): return any(k.lower() in text.lower() for k in kws)