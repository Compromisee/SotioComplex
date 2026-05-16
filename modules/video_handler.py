import yt_dlp, os, uuid, random, glob
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips

class VideoHandler:
    def __init__(self, logger, video_dir='output/videos', stock_dir='stock', music_dir='music', preview_dir='output/previews'):
        self.logger = logger
        self.dir = video_dir; self.stock_dir = stock_dir; self.music_dir = music_dir; self.preview_dir = preview_dir
        for d in [video_dir, stock_dir, music_dir, preview_dir]: os.makedirs(d, exist_ok=True)

    def fetch_background(self, prompt="", url="", shorts=True, cache=None):
        # Try cache
        key = url or prompt
        if cache:
            c = cache.get("video", key)
            if c and os.path.exists(c): return c
        try:
            search = url if url else f"ytsearch1:{prompt} no copyright background loop"
            out = f"{self.dir}/bg_{uuid.uuid4().hex[:8]}.mp4"
            with yt_dlp.YoutubeDL({'format':'best[height<=720]','outtmpl':out,'quiet':True,'noplaylist':True}) as ydl:
                ydl.download([search])
            if cache: cache.set(out, "video", key)
            self.logger.log("BG downloaded","success")
            return out
        except Exception as e:
            self.logger.log(f"YT failed → using stock pool: {e}","warn")
            return self._stock_fallback()

    def _stock_fallback(self):
        """#10 Stock footage pool"""
        stocks = glob.glob(f"{self.stock_dir}/*.mp4")
        if stocks:
            pick = random.choice(stocks)
            self.logger.log(f"Stock: {pick}","info")
            return pick
        self.logger.log("No stock fallback available","error"); return None

    def _pick_music(self):
        """#9 Music library"""
        tracks = glob.glob(f"{self.music_dir}/*.mp3")
        return random.choice(tracks) if tracks else None

    def build_video(self, bg_path, text, audio_path=None, shorts=True, split=True, captions_words=None, add_music=True):
        if not bg_path or not os.path.exists(bg_path):
            self.logger.log("No bg","error"); return []
        outs = []
        try:
            clip = VideoFileClip(bg_path)
            w, h = (1080,1920) if shorts else (1920,1080)
            words = text.split(); chunks = [text]
            if split and len(words) > 40:
                mid = len(words)//2
                chunks = [' '.join(words[:mid]), ' '.join(words[mid:])]
            for i, chunk in enumerate(chunks):
                dur = min(clip.duration, max(8, len(chunk.split())*0.45))
                seg = clip.subclip(0, dur).resize(newsize=(w,h))
                layers = [seg]

                # Word-level highlighted captions (#8)
                if captions_words:
                    for word_data in captions_words:
                        if word_data['start'] < dur:
                            wt = TextClip(word_data['word'], fontsize=72, color='yellow',
                                          stroke_color='black', stroke_width=4,
                                          font='Arial-Bold' if os.name!='nt' else 'Arial')
                            wt = wt.set_position('center').set_start(word_data['start']).set_end(min(word_data['end'], dur))
                            layers.append(wt)
                else:
                    txt = TextClip(chunk, fontsize=48, color='white', stroke_color='black',
                                  stroke_width=3, size=(w-120,None), method='caption')\
                                  .set_position('center').set_duration(dur)
                    layers.append(txt)

                final = CompositeVideoClip(layers)

                # Audio mixing (voiceover + music) #9
                audio_clips = []
                if audio_path and os.path.exists(audio_path):
                    a = AudioFileClip(audio_path)
                    audio_clips.append(a.subclip(0, min(dur, a.duration)))
                if add_music:
                    mp = self._pick_music()
                    if mp:
                        m = AudioFileClip(mp).volumex(0.15)
                        audio_clips.append(m.subclip(0, min(dur, m.duration)))
                if audio_clips:
                    final = final.set_audio(CompositeAudioClip(audio_clips))

                out = f"{self.dir}/vid_{uuid.uuid4().hex[:8]}_p{i+1}.mp4"
                final.write_videofile(out, codec='libx264', audio_codec='aac', fps=24, logger=None)
                outs.append(out)
                self.logger.preview('video', out)  # #2 live preview
                self.logger.log(f"Video {i+1}: {out}","success")

                # Save preview frame
                try:
                    frame = final.get_frame(dur/2)
                    from PIL import Image
                    pv = f"{self.preview_dir}/pv_{uuid.uuid4().hex[:6]}.jpg"
                    Image.fromarray(frame).save(pv, quality=70)
                    self.logger.preview('frame', pv)
                except: pass

            clip.close()
        except Exception as e:
            self.logger.log(f"Video err: {e}","error")
        return outs