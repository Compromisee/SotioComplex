from PIL import Image, ImageDraw, ImageFont
import uuid, os, textwrap

class ThumbnailGenerator:
    def __init__(self, logger, thumb_dir='output/thumbnails'):
        self.logger = logger; self.dir = thumb_dir
        os.makedirs(thumb_dir, exist_ok=True)

    def generate(self, title, theme='tech'):
        styles = {'tech':{"bg":(15,15,40),"text":"yellow","accent":(255,200,0)},
                  'finance':{"bg":(10,40,20),"text":"white","accent":(0,200,100)},
                  'news':{"bg":(180,20,20),"text":"white","accent":(255,255,255)},
                  'sports':{"bg":(20,20,20),"text":"orange","accent":(255,140,0)},
                  'blog':{"bg":(250,250,250),"text":"black","accent":(0,100,255)}}
        s = styles.get(theme, styles['tech'])
        try:
            img = Image.new('RGB',(1280,720),color=s['bg'])
            d = ImageDraw.Draw(img)
            try: font = ImageFont.truetype("arialbd.ttf", 80)
            except: font = ImageFont.load_default()
            d.rectangle([(0,640),(1280,720)], fill=s['accent'])
            wr = textwrap.fill(title[:100], width=18)
            b = d.multiline_textbbox((0,0), wr, font=font)
            w,h = b[2]-b[0], b[3]-b[1]
            d.multiline_text(((1280-w)/2+4,(720-h)/2+4), wr, font=font, fill='black', align='center', spacing=15)
            d.multiline_text(((1280-w)/2,(720-h)/2), wr, font=font, fill=s['text'], align='center', spacing=15)
            out = f"{self.dir}/thumb_{uuid.uuid4().hex[:8]}.png"
            img.save(out)
            self.logger.preview('image', out)
            return out
        except Exception as e: self.logger.log(f"thumb: {e}","error"); return None