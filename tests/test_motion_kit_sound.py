import os
import tempfile
import unittest
from pathlib import Path
import numpy as np
from film_factory.sound import build

class MotionKitSoundTests(unittest.TestCase):
    def test_timed_scene_change_produces_stereo_foley(self):
        old=os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as root:
                os.chdir(root)
                Path("output").mkdir()
                result=build(4.5,[{"start":0,"end":2},{"start":2,"end":4.5}],"science",words=[])
                self.assertTrue(Path("output/effects.wav").exists())
                self.assertTrue(any(e["kind"]=="scene_whoosh" and abs(e["at"]-2)<1e-6 for e in result["events"]))
        finally:
            os.chdir(old)
if __name__=="__main__": unittest.main()
