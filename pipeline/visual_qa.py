"""Compare rendered logo pixels to the immutable source, without editing the source."""
import json,sys
from pathlib import Path
from PIL import Image,ImageOps,ImageChops,ImageStat
image_path,logo_dir,manifest_path,output=sys.argv[1:]
manifest=json.loads(Path(manifest_path).read_text())
source=Image.open(Path(logo_dir)/Path(manifest['path']).name).convert('RGB')
expected=Image.new('RGB',(132,132),manifest['badgeBackground'])
scaled=ImageOps.contain(source,(132,132),Image.Resampling.LANCZOS)
expected.paste(scaled,((132-scaled.width)//2,(132-scaled.height)//2))
actual=Image.open(image_path).convert('RGB').crop((868,170,1000,302))
box=(14,14,118,118)
diff=ImageStat.Stat(ImageChops.difference(actual.crop(box),expected.crop(box)))
mae=sum(diff.mean)/3
report={'mean_absolute_rgb_error':mae,'threshold':15,'passed':mae<=15,'region':[868,170,1000,302],'source_sha256':manifest['sha256'],'note':'Rendered thumbnail pixel check, excluding rounded border; exact source bytes are separately hash-verified.'}
Path(output).write_text(json.dumps(report,indent=2))
if not report['passed']:raise SystemExit('LOGO_RENDERED_PIXELS_MISMATCH')
