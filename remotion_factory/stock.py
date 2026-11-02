"""An occupied slot is valid only for the retained complete movie and exact receipts."""
from .health import check_posts,episode_for,original_release_url,verify_media,AuditFailure,CAIRO
from .publish import instant

def verify_occupied(profile,mapping,queues,due):
 receipts,url=check_posts(mapping,queues,instant(due),'prepublish')
 episode=episode_for(instant(due).astimezone(CAIRO).date(),url,receipts)
 if original_release_url(episode)!=url:raise AuditFailure('Occupied slot references a replacement media URL; preserve posts and require reconciliation')
 technical=verify_media(url,episode,profile)
 if not technical.get('passed'):raise AuditFailure('Occupied slot failed independent complete-video checks')
 return {'retained_post_ids_verified':True,'original_release_verified':True,'video_sha256':episode['expected_sha256'],'duration':technical['duration'],'technical_passed':True}
