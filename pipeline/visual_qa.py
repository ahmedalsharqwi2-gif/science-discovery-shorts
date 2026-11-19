"""Compare rendered brand mark to the immutable source, without editing the source.
Classic mode composites the owner-supplied logo.png badge at [868,170,1000,302]:
pixel-compare that region. Paper mode renders the brand as a text wordmark
(channelName) top-right instead, so verify wordmark presence by ink density."""
import json,sys
from pathlib import Path
from PIL import Image,ImageOps,ImageChops,ImageStat
image_path,logo_dir,manifest_path,output=sys.argv[1:5]
mode=sys.argv[5] if len(sys.argv)>5 else 'classic'
manifest=json.loads(Path(manifest_path).read_text())
if mode=='paper':
    actual=Image.open(image_path).convert('RGB')
    region=(780,15,1040,75)
    box=actual.crop(region)
    px=box.load()
    dark=sum(1 for y in range(box.height) for x in range(box.width) if sum(px[x,y])<420)
    report={'mode':'paper','wordmark_ink_pixels':dark,'threshold':100,'passed':dark>=100,'region':list(region),'source_sha256':manifest['sha256'],'note':'Paper mode renders the brand as a text wordmark top-right; pixel-exact logo compare applies to classic mode only. Exact source bytes are separately hash-verified.'}
    Path(output).write_text(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit('BRAND_WORDMARK_MISSING')
    sys.exit(0)
source=Image.open(Path(logo_dir)/Path(manifest['path']).name).convert('RGB')
expected=Image.new('RGB',(132,132),manifest['badgeBackground'])
scaled=ImageOps.contain(source,(132,132),Image.Resampling.LANCZOS)
expected.paste(scaled,((132-scaled.width)//2,(132-scaled.height)//2))
actual=Image.open(image_path).convert('RGB').crop((868,170,1000,302))
box=(14,14,118,118)
diff=ImageStat.Stat(ImageChops.difference(actual.crop(box),expected.crop(box)))
mae=sum(diff.mean)/3
report={'mode':'classic','mean_absolute_rgb_error':mae,'threshold':15,'passed':mae<=15,'region':[868,170,1000,302],'source_sha256':manifest['sha256'],'note':'Rendered thumbnail pixel check, excluding rounded border; exact source bytes are separately hash-verified.'}
Path(output).write_text(json.dumps(report,indent=2))
if not report['passed']:raise SystemExit('LOGO_RENDERED_PIXELS_MISMATCH')
