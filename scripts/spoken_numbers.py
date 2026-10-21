"""Expand numerals before TTS; captions use the same spoken words."""
import re
from num2words import num2words
_DIGITS=str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹','01234567890123456789')
_PATTERN=re.compile(r'[+-]?\d+(?:[,٬]\d{3})*(?:[.٫]\d+)?')
def spoken_numbers(text):
    text=str(text).translate(_DIGITS)
    def expand(match):
        raw=match.group().replace(',','').replace('٬','').replace('٫','.')
        sign='سالب ' if raw.startswith('-') else ''
        raw=raw.lstrip('+-')
        if '.' in raw:
            whole,fraction=raw.split('.')
            return sign+num2words(int(whole),lang='ar')+' فاصلة '+' '.join(num2words(int(d),lang='ar') for d in fraction)
        return sign+num2words(int(raw),lang='ar')
    rendered=_PATTERN.sub(lambda m:' '+expand(m)+' ',text)
    return re.sub(r'\s+',' ',rendered.replace('%',' في المية ').replace('٪',' في المية ')).strip()
