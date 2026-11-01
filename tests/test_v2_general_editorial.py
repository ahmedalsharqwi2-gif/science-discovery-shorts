import unittest
from copy import deepcopy
from production_v2.general_editorial import validate,editor
class GeneralEditorialTests(unittest.TestCase):
 def story(self):
  return {'profile':'science','topic_key':'knowledge-cell-membrane','knowledge_category':'biology','scenes':[
   {'id':str(i),'label':'تركيب الخلية','narration':'فقرة مصرية عن الخلية','environment':'laboratory','visual_change':'تظهر طبقات الخلية وحركة مكوناتها','camera_start':[0,1,13],'camera_end':[1,1,11],
    'objects':[{'kind':kind,'position':[j-1,i*.1,0],'scale':[1,1,1],'rotation':[0,0,0],'color':'#78acbd','motion':'pulse'} for j,kind in enumerate(['cell','leaf','molecule'])]} for i in range(8)]}
 def test_biology_film_needs_no_external_source_or_nasa_identity(self):
  result=validate(self.story(),'science')
  self.assertEqual(result['visual_plan']['world'],'procedural_story')
  self.assertNotIn('source',result)
 def test_unsupported_geometry_and_repeated_slide_layouts_are_rejected(self):
  s=self.story();s['scenes'][0]['objects'][0]['kind']='execute-javascript'
  with self.assertRaises(ValueError):validate(s,'science')
  s=self.story();s['scenes']=[deepcopy(s['scenes'][0]) for i in range(8)]
  with self.assertRaises(ValueError):validate(s,'science')
 def test_editor_restores_existing_author_on_failure(self):
  import types
  original=lambda *args:None
  module=types.SimpleNamespace(prepare=original)
  with self.assertRaises(RuntimeError):
   with editor(module,'science'):raise RuntimeError('interrupted')
  self.assertIs(module.prepare,original)
if __name__=='__main__':unittest.main()
