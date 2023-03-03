from unittest import TestCase

from utils.word_match import is_multi_round


class Test(TestCase):
    def test_is_multi_round(self):
        print(is_multi_round("环评的条件",
                             "固定资产投资项目合理用能审查"))
