"""Official history candidates whose authored geometry has an explicit contract.

UNESCO's public XML list replenishes the bank. Unsupported monuments are omitted;
a pyramid, dome or amphitheatre name alone cannot justify an unrelated facade.
"""
from __future__ import annotations
import json,re
from datetime import datetime,timezone
from pathlib import Path
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent
XML_URL='https://whc.unesco.org/en/list/xml/'
HEADERS={'User-Agent':'ArabicDocumentaryMotion/2.0'}
COUNT={'one':1,'two':2,'three':3,'1':1,'2':2,'3':3}

def canonical_site(identifier):
    raw=str(identifier).strip()
    if not re.fullmatch(r'[1-9][0-9]{0,5}',raw):raise ValueError('Invalid official UNESCO site ID')
    return f'https://whc.unesco.org/en/list/{int(raw)}/'

def _plain(value):
    return ' '.join(BeautifulSoup(str(value or ''),'html.parser').get_text(' ',strip=True).split())

def _fields(element):
    return {child.tag.rsplit('}',1)[-1]:''.join(child.itertext()).strip() for child in element}

def _tier_count(text,focus):
    structure=r'aqueduct' if focus=='aqueduct' else r'(?:amphitheat(?:re|er)|colosseum)'
    count=r'(one|two|three|1|2|3)[ -]+(?:superimposed[ -]+)?(?:tiers?|levels?|storeys?|stories)'
    for expression in (structure+r'([^.!?]{0,90}?)\b'+count, r'\b'+count+r'[^.!?]{0,35}?'+structure):
        match=re.search(expression,text,re.I)
        if not match:continue
        if re.search(r'church|houses?|palace|cathedral|residential|tower',match.group(0),re.I):continue
        values=[x.lower() for x in match.groups() if x and x.lower() in COUNT]
        if values:return COUNT[values[-1]]
    return None

def visual_contract(identifier,title,description):
    """Return only supported, source-described structure types; never guess tiers."""
    identifier=str(identifier);text=(title+' '+description).lower()
    # Verified complete source pages; exact views are limited to their focal structure.
    known={
        '344':{'focus':'aqueduct','tier_count':3},
        '311':{'focus':'aqueduct','tier_count':2},
        '164':{'focus':'arena','tier_count':2},
        '86':{'focus':'pyramid','shape':'smooth_sided','scope':'Focus on the smooth-sided Giza pyramids; do not use this model for the stepped pyramid at Saqqara.'},
    }
    if identifier in known:result=dict(known[identifier])
    elif 'aqueduct' in text:
        tiers=_tier_count(text,'aqueduct')
        if tiers is None:return None
        result={'focus':'aqueduct','tier_count':tiers}
    elif re.search(r'amphitheat(?:re|er)|colosseum',text):
        tiers=_tier_count(text,'arena')
        if tiers is None:return None
        result={'focus':'arena','tier_count':tiers}
    elif 'pyramid' in text and re.search(r'smooth[- ]sided|steep[- ]sided',text) and not re.search(r'stepped|step[- ]pyramid|terraced|maya|aztec',text):
        result={'focus':'pyramid','shape':'smooth_sided'}
    else:return None
    focus=result['focus']
    result['diagram_only']=True
    result['allowed_modes']={
        'aqueduct':['hero','levels','arch','section','water','material','assembly'],
        'arena':['hero','levels','arch','section','material','assembly'],
        'pyramid':['hero','levels','section','material','assembly'],
    }[focus]
    result['forbidden_features']=['dome_ribs','oculus']+(['arches'] if focus=='pyramid' else [])
    result.setdefault('scope','Show only the stated focal structure as a schematic; do not claim a surveyed replica of the whole heritage site or invent construction measurements.')
    return result

def parse_candidates(content):
    tree=ET.fromstring(content);result=[];seen=set()
    for node in tree.iter():
        if node.tag.rsplit('}',1)[-1]!='row':continue
        row=_fields(node);identifier=row.get('id_number','')
        try:url=canonical_site(identifier)
        except ValueError:continue
        if url in seen:continue
        category=row.get('category','').casefold()
        if category and category not in {'cultural','mixed'}:continue
        title=_plain(row.get('site') or row.get('site_name'))
        description=_plain(row.get('short_description'))
        if not title or len(description)<100:continue
        contract=visual_contract(identifier,title,description)
        if contract is None:continue
        seen.add(url)
        result.append({'key':'unesco-'+identifier+'-'+contract['focus'],'family':'architecture','variant':contract['focus'],'title':title,'publisher':'UNESCO World Heritage Centre','url':url,'visual_contract':contract})
    return result

def candidates(now=None,fetch=None):
    """Return the verified starter bank plus supported, stable daily XML candidates.

    An XML outage preserves verified source choices; it never creates made-up facts
    or silently substitutes a building with unsupported geometry.
    """
    now=now or datetime.now(timezone.utc);fetch=fetch or requests.get
    bank=json.loads((ROOT/'catalog.json').read_text())['history']
    rows=[r for r in bank if r.get('url','').startswith('https://whc.unesco.org/en/list/') and r.get('visual_contract')]
    seen={r['url'].rstrip('/') for r in rows}
    try:
        response=fetch(XML_URL,headers=HEADERS,timeout=35);response.raise_for_status()
        fresh=parse_candidates(response.content)
    except (requests.RequestException,ET.ParseError,ValueError):return rows
    # Rotate deterministic order without adding a random or changed URL identity.
    import hashlib
    day=now.date().isoformat()
    fresh.sort(key=lambda r:hashlib.sha256((day+r['key']).encode()).hexdigest())
    for row in fresh:
        if row['url'].rstrip('/') not in seen:rows.append(row);seen.add(row['url'].rstrip('/'))
    return rows
