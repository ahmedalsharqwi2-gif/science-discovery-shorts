"""Keep actual image authors, licenses and source links in new post captions."""
def format_credits(assets):
 rows=[];seen=set()
 for item in assets:
  url=item.get('attribution_url') or item.get('page')
  key=url or item.get('original_download_sha256') or item.get('id') or item.get('file')
  if not key or key in seen:continue
  seen.add(key);artist=' '.join(str(item.get('artist') or 'Public domain').split())[:180];license=' '.join(str(item.get('license') or 'See source license').split())[:60]
  rows.append(artist+' — '+license+((' — '+url) if url else ''))
 return '\n'.join(rows[:3])
