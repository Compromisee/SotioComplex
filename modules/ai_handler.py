import requests
from langdetect import detect

class AIHandler:
    def __init__(self, logger, config, presets, cache=None):
        self.logger = logger; self.config = config; self.presets = presets; self.cache = cache
        self.ollama_url = config['ai']['ollama_url']
        self.lmstudio_url = config['ai']['lmstudio_url']

    def detect_models(self):
        local = []
        try:
            r = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            local += [{"provider":"ollama","name":m['name']} for m in r.json().get('models',[])]
        except: pass
        try:
            r = requests.get(f"{self.lmstudio_url}/v1/models", timeout=3)
            local += [{"provider":"lmstudio","name":m['id']} for m in r.json().get('data',[])]
        except: pass
        self.logger.log(f"Detected {len(local)} local models","success")
        return {"local": local, "providers": self.config['ai']['providers'], "fallback_api": not local}

    def detect_language(self, text):
        try: return detect(text[:500])
        except: return "unknown"

    def summarize(self, text, provider='ollama', model='llama3', style='concise', api_key='', translate_to=None):
        tpl = self.presets['prompt_presets'].get(style, self.presets['prompt_presets']['concise'])
        prompt = f"{tpl}\n\nArticle:\n{text[:4000]}"
        if translate_to: prompt = f"Respond in {translate_to}. " + prompt
        if self.cache:
            c = self.cache.get("ai", provider, model, style, text[:200])
            if c: return c
        result = ""
        try:
            if provider == 'ollama': result = self._ollama(prompt, model)
            elif provider == 'openai': result = self._openai(prompt, api_key, model or "gpt-4o-mini")
            elif provider == 'anthropic': result = self._anthropic(prompt, api_key, model or "claude-3-haiku-20240307")
            elif provider == 'groq': result = self._groq(prompt, api_key, model or "llama3-8b-8192")
            elif provider == 'gemini': result = self._gemini(prompt, api_key)
            elif provider == 'openrouter': result = self._openrouter(prompt, api_key, model)
            elif provider == 'lmstudio': result = self._lmstudio(prompt, model)
        except Exception as e:
            self.logger.log(f"{provider} err: {e}","error")
        if self.cache and result:
            self.cache.set(result, "ai", provider, model, style, text[:200])
        return result

    def _ollama(self, prompt, model):
        r = requests.post(f"{self.ollama_url}/api/generate", json={"model":model,"prompt":prompt,"stream":False}, timeout=180)
        return r.json().get('response','').strip()

    def _lmstudio(self, prompt, model):
        r = requests.post(f"{self.lmstudio_url}/v1/chat/completions",
            json={"model":model,"messages":[{"role":"user","content":prompt}]}, timeout=180)
        return r.json()['choices'][0]['message']['content']

    def _openai(self, prompt, key, model):
        from openai import OpenAI
        return OpenAI(api_key=key).chat.completions.create(model=model, messages=[{"role":"user","content":prompt}]).choices[0].message.content

    def _anthropic(self, prompt, key, model):
        import anthropic
        r = anthropic.Anthropic(api_key=key).messages.create(model=model, max_tokens=1024, messages=[{"role":"user","content":prompt}])
        return r.content[0].text

    def _groq(self, prompt, key, model):
        from groq import Groq
        return Groq(api_key=key).chat.completions.create(model=model, messages=[{"role":"user","content":prompt}]).choices[0].message.content

    def _gemini(self, prompt, key):
        import google.generativeai as g
        g.configure(api_key=key)
        return g.GenerativeModel('gemini-1.5-flash').generate_content(prompt).text

    def _openrouter(self, prompt, key, model):
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization":f"Bearer {key}"},
            json={"model":model or "meta-llama/llama-3-8b-instruct","messages":[{"role":"user","content":prompt}]})
        return r.json()['choices'][0]['message']['content']