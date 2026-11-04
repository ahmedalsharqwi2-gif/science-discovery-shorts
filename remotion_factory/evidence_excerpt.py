"""Narrow only existing model-supplied excerpts to a literal source span."""
import copy
def literal_excerpt(quote,source):
 if not isinstance(quote,str):return quote
 words=quote.split();normalized=' '.join(source.split())
 if 4<=len(words)<=18 and ' '.join(words) in normalized:return ' '.join(words)
 for size in range(min(18,len(words)),3,-1):
  starts=sorted(range(len(words)-size+1),key=lambda i:abs(i+size/2-len(words)/2))
  for start in starts:
   candidate=' '.join(words[start:start+size])
   if candidate in normalized:return candidate
 return quote  # The original validator still rejects absent or fabricated evidence.
def narrow_excerpts(story,source):
 result=copy.deepcopy(story)
 for scene in result.get('scenes',[]):
  scene['evidence_quote']=literal_excerpt(scene.get('evidence_quote',''),source)
 return result
