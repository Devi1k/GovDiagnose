from unittest import TestCase

from utils.ai_wrapper import get_faq_from_service


class Test(TestCase):
    def test_get_faq_from_service(self):
        score, answer, service = get_faq_from_service("培训学校民办文化的负责人",
                                                      "实施中等及中等以下学历教育、学前教育、自学考试助学和实施高等以下非学历文化教育的民办学校的筹设、设立、变更、延续与终止的许可-实施非学历文化教育、自学考试助学的教育机构的许可-筹设、设立")  # add assertion here
        print(score, answer)
        # self.fail()
