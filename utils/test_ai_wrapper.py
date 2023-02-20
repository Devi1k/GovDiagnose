from unittest import TestCase

from utils.ai_wrapper import get_recommend


class Test(TestCase):
    def test_get_recommend(self):
        res = get_recommend(
            service_name='户外广告及临时悬挂、设置标语或者宣传品许可-户外广告设施许可（不含公交候车亭附属广告及公交车体广告设施）（市级权限委托市内六区实施）',
            history=['我想挂个招牌', '规划预留户外广告设施牌匾除外的设计图纸有什么要求', '需要收费吗'])
        print(res)
