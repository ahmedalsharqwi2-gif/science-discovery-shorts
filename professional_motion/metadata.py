"""Topic-specific publication title and relevant hashtags, without transcript dumps."""
import re
from .editorial import BRANDS

def clean_tag(value):
    value=str(value).strip().lstrip('#').replace(' ','_')
    if not re.fullmatch(r'[\w\u0621-\u064a]{2,50}',value):raise ValueError('Use concise topic hashtags containing letters, digits or underscores')
    return value

def validate_tags(story):
    tags=list(dict.fromkeys(clean_tag(t) for t in story.get('hashtags',[])))
    if not 3<=len(tags)<=5:raise ValueError('Provide three to five distinct relevant topic hashtags')
    if any(t.lower() in {'fyp','viral','trending','اكسبلور','ترند'} for t in tags):raise ValueError('Use topic-relevant hashtags instead of unrelated reach bait')
    corpus=' '.join([story['title'],story.get('canonical_subject','').replace('-',' '),*[s['narration'] for s in story['scenes']]])
    def norm(t):return re.sub(r'[^\w\u0621-\u064a]','',t).lower().translate(str.maketrans({'أ':'ا','إ':'ا','آ':'ا','ة':'ه','ى':'ي'}))
    words={norm(w) for w in corpus.split()}
    topical=sum(any(len(norm(w))>=3 and norm(w) in words for w in tag.split('_')) for tag in tags)
    if topical<2:raise ValueError('At least two hashtags must refer to specific subjects actually discussed in this film')
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
