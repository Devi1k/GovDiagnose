from unittest import TestCase

from utils.ai_wrapper import get_faq_from_service


class Test(TestCase):
    def test_get_faq_from_service(self):
        score, answer, service = get_faq_from_service("满足什么材料",
                                                      "户外广告及临时悬挂、设置标语或者宣传品许可-户外广告设施许可（不含公交候车亭附属广告及公交车体广告设施）（市级权限委托市内六区实施）")  # add assertion here
        print(score, answer)
        # self.fail()
