"""Topic-specific publication title and relevant hashtags, without transcript dumps."""
import re
from .editorial import BRANDS
from .style_warnings import note

def clean_tag(value):
    value=str(value).strip().lstrip('#').replace(' ','_')
    if not re.fullmatch(r'[\w\u0621-\u064a]{2,50}',value):raise ValueError('Use concise topic hashtags containing letters, digits or underscores')
    return value

def validate_tags(story,context=""):
    tags=[]
    for value in story.get('hashtags',[]):
        try:tag=clean_tag(value)
        except ValueError:
            note(story,'A malformed hashtag was omitted from publication metadata');continue
        if tag.lower() in {'fyp','viral','trending','اكسبلور','ترند'}:
            note(story,'An unrelated reach bait hashtag was omitted');continue
        if tag not in tags:tags.append(tag)
    if not 3<=len(tags)<=5:note(story,'Provide three to five distinct relevant topic hashtags')
    if len(tags)<3:
        candidates=[story.get('title',''),story.get('canonical_subject','').replace('-',' '),*[x.get('label','') for x in story.get('scenes',[])],story.get('source',{}).get('publisher','')]
        for candidate in candidates:
            tag=re.sub(r'[^\w\u0621-\u064a]+','_',' '.join(str(candidate).split()[:5])).strip('_')[:50].strip('_')
            if len(tag)>=2 and tag not in tags:tags.append(tag)
            if len(tags)>=3:break
    corpus=' '.join([story['title'],story.get('canonical_subject','').replace('-',' '),*[s['narration'] for s in story['scenes']],context,story.get('source',{}).get('title','')])
    def norm(t):
        t=re.sub(r'[^\w\u0621-\u064a]','',t).lower().translate(str.maketrans({'أ':'ا','إ':'ا','آ':'ا','ة':'ه','ى':'ي'}))
        if t.startswith(('بال','وال','فال','كال')) and len(t)>5:t=t[1:]
        if t.startswith('ال') and len(t)>4:t=t[2:]
        return t
    words={norm(w) for w in corpus.split()}
    topical=sum(any(len(norm(w))>=3 and norm(w) in words for w in tag.split('_')) for tag in tags)
    if topical<2:note(story,'At least two hashtags must refer to specific subjects actually discussed in this film')
    story['hashtags']=tags;return tags

def make(story,profile):
    tags=validate_tags(story);title=re.sub(r'\s+',' ',story['title']).strip()
    if not title.startswith(BRANDS[profile]):title=BRANDS[profile]+' | '+title
    title=title[:100].rstrip(' |،')
    source=story['source'];source_url=source.get('url','')
    if story.get('fiction') is True:
        caption=' '.join(story.get('description','').split())+'\n'+' '.join('#'+t for t in tags)
    else:
        disclosure='رسوم توضيحية وإعادة تمثيل درامية؛ ليست تسجيلًا للأحداث.'
        if profile=='news':disclosure+=' القفشات تعليق ساخر، والخبر من المصدر.'
        caption=disclosure+'\nالمصدر: '+source['publisher']+'\n'+source_url+'\n'+' '.join('#'+t for t in tags)
    return {'title':title,'caption':caption,'description':caption,'tags':tags,'hashtags':['#'+t for t in tags],'source_url':source_url,'containsSyntheticMedia':True}
