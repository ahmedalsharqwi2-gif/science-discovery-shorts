import os
def display_title(title):
 brand=os.environ['CHANNEL_BRAND'];title=' '.join(str(title).split())
 return (title if title.startswith(brand) else brand+' | '+title)[:100]
