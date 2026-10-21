"""Register regressions: a factual script must still sound like spoken Egyptian."""
import unittest
from scripts.source_episode import egyptian_style

class SourceStyleTests(unittest.TestCase):
    def test_formal_science_copy_is_not_accepted_as_egyptian(self):
        self.assertFalse(egyptian_style("تعتبر المفارقة أن شفرة المروحة ليست مفرودة، حيث إن طرف الشفرة يتحرك أسرع من الجزء القريب من المحور."))

    def test_spoken_egyptian_example_is_accepted(self):
        self.assertTrue(egyptian_style("بص، ده طرف الشفرة اللي بيتحرك أسرع. ليه؟ عشان المسافة أكبر. دي فكرة بسيطة، مش كل جزء بيتحرك بنفس السرعة، وكده الزوايا بتختلف."))
