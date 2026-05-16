from PIL import Image, ImageDraw, ImageFont
import uuid, textwrap, os, random

class ImageHandler:
    def __init__(self, logger, image_dir='output/images'):
        self.logger = logger; self.dir = image_dir
        os.makedirs(image_dir, exist_ok=True)
        self.themes = [
            {"bg":(20,20,25),"fg":"white","accent":(99,102,241)},
            {"bg":(245,245,250),"fg":"black","accent":(239,68,68)},
            {"bg":(10,40,60),"fg":"white","accent":(34,197,94)}]

    def create_cards(self, text, count=2):
        words = text.split(); per = max(1,len(words)//count)
        chunks = [' '.join(words[i*per:(i+1)*per]) for i in range(count)]
        outs = []
        for i, c in enumerate(chunks):
            p = self._render(c, i)
            if p: outs.append(p)
        return outs

    def _render(self, text, idx):
        try:
            t = random.choice(self.themes)
            img = Image.new('RGB',(1080,1080),color=t['bg'])
            d = ImageDraw.Draw(img)
            try: font = ImageFont.truetype("arial.ttf", 44)
            except: font = ImageFont.load_default()
            d.rectangle([(0,0),(20,1080)], fill=t['accent'])
            wr = textwrap.fill(text, width=28)
            b = d.multiline_textbbox((0,0), wr, font=font)
            w,h = b[2]-b[0], b[3]-b[1]
            d.multiline_text(((1080-w)/2,(1080-h)/2), wr, font=font, fill=t['fg'], align='center', spacing=12)
            out = f"{self.dir}/card_{uuid.uuid4().hex[:8]}_{idx}.png"
            img.save(out)
            self.logger.preview('image', out)
            return out
        except Exception as e: self.logger.log(f"img: {e}","error"); return None