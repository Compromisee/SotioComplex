import asyncio, edge_tts, uuid, os, re, requests

class TTSHandler:
    def __init__(self, logger, audio_dir='output/audio'):
        self.logger = logger; self.dir = audio_dir
        os.makedirs(audio_dir, exist_ok=True)

    def generate(self, text, voice='en-US-AriaNeural'):
        try:
            out = f"{self.dir}/tts_{uuid.uuid4().hex[:8]}.mp3"
            asyncio.run(edge_tts.Communicate(text, voice).save(out))
            self.logger.log(f"TTS: {out}","success")
            return out
        except Exception as e:
            self.logger.log(f"TTS: {e}","error"); return None

    def generate_dialogue(self, text, voice_a='en-US-GuyNeural', voice_b='en-US-AriaNeural'):
        """Parse HOST:/GUEST: dialogue, render alternating voices, concat"""
        try:
            from moviepy.editor import AudioFileClip, concatenate_audioclips
            lines = re.findall(r'(HOST|GUEST):\s*(.+?)(?=\n(?:HOST|GUEST):|$)', text, re.S)
            if not lines:
                return self.generate(text, voice_a)
            clips = []
            for who, line in lines:
                voice = voice_a if who == 'HOST' else voice_b
                out = f"{self.dir}/seg_{uuid.uuid4().hex[:6]}.mp3"
                asyncio.run(edge_tts.Communicate(line.strip(), voice).save(out))
                clips.append(AudioFileClip(out))
            final = concatenate_audioclips(clips)
            out = f"{self.dir}/dialogue_{uuid.uuid4().hex[:8]}.mp3"
            final.write_audiofile(out, logger=None)
            self.logger.log(f"Dialogue TTS: {out}","success")
            return out
        except Exception as e:
            self.logger.log(f"Dialogue TTS: {e}","error"); return None

    def clone_voice(self, text, sample_path, elevenlabs_key=""):
        """Voice cloning via ElevenLabs (#34)"""
        if not elevenlabs_key:
            self.logger.log("No ElevenLabs key — falling back to default voice","warn")
            return self.generate(text)
        try:
            # Upload sample (simplified)
            r = requests.post("https://api.elevenlabs.io/v1/voices/add",
                headers={"xi-api-key":elevenlabs_key},
                data={"name":f"clone_{uuid.uuid4().hex[:6]}"},
                files={"files":open(sample_path,'rb')})
            voice_id = r.json().get('voice_id')
            r2 = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key":elevenlabs_key, "Content-Type":"application/json"},
                json={"text":text})
            out = f"{self.dir}/clone_{uuid.uuid4().hex[:8]}.mp3"
            with open(out,'wb') as f: f.write(r2.content)
            self.logger.log(f"Cloned voice: {out}","success")
            return out
        except Exception as e:
            self.logger.log(f"Clone fail: {e}","error"); return None