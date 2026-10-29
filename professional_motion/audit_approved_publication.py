"""Read-only provider delivery audit for the explicitly approved eclipse."""
import json
from pathlib import Path
from film_factory.publish import query

def main():
 stock=json.loads(Path('state/publication_stock.json').read_text());entry=stock['slots']['immediate approved-eclipse-40845210819'];rows=[]
 for service,receipt in entry['receipts'].items():
  row={'service':service,'id':receipt['id']}
  try:row.update(query('query { post(input: {id: '+json.dumps(receipt['id'])+'}) { id status dueAt sentAt externalLink } }')['post'])
  except Exception as error:row['audit_error']=type(error).__name__
  rows.append(row)
 p=Path('professional_motion/delivery');p.mkdir(parents=True,exist_ok=True);(p/'eclipse-delivery-audit.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print(json.dumps(rows,ensure_ascii=False))
if __name__=='__main__':main()
