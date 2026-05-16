import os, json

class WhisperHandler:
    def __init__(self, logger):
        self.logger = logger
        self.model = None

    def _load(self):
        if self.model is None:
            import whisper
            self.logger.log("Loading Whisper tiny model...","info")
            self.model = whisper.load_model("tiny")
        return self.model

    def transcribe(self, audio_path):
        """Returns word-level timestamps for caption highlight"""
        try:
            m = self._load()
            r = m.transcribe(audio_path, word_timestamps=True)
            words = []
            for seg in r.get('segments', []):
                for w in seg.get('words', []):
                    words.append({"word": w['word'].strip(), "start": w['start'], "end": w['end']})
            self.logger.log(f"Whisper: {len(words)} words timed","success")
            return words
        except Exception as e:
            self.logger.log(f"Whisper: {e}","error"); return []

    def to_srt(self, words, out_path):
        try:
            lines = []
            i = 1
            chunk = []
            for w in words:
                chunk.append(w)
                if len(chunk) >= 5 or w['word'].endswith(('.','!','?')):
                    s, e = chunk[0]['start'], chunk[-1]['end']
                    txt = ' '.join(x['word'] for x in chunk)
                    lines.append(f"{i}\n{self._t(s)} --> {self._t(e)}\n{txt}\n")
                    i += 1; chunk = []
            with open(out_path,'w',encoding='utf-8') as f: f.write('\n'.join(lines))
            return out_path
        except Exception as e:
            self.logger.log(f"SRT: {e}","error"); return None

    def _t(self, s):
        h=int(s//3600); m=int((s%3600)//60); sec=int(s%60); ms=int((s-int(s))*1000)
        return f"{h:02}:{m:02}:{sec:02},{ms:03}"