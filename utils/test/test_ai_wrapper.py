from unittest import TestCase

from utils.ai_wrapper import get_faq_from_service


class Test(TestCase):
    def test_get_faq_from_service(self):
        # score, answer, service = get_faq_from_service("需要第三方吗",
        #                                               "固定资产投资项目合理用能审查")  # add assertion here
        sentence = "我想办理固定资产投资项目合理用能审查需要什么材料"

        service = "固定资产投资项目合理用能审查"

        score, answer, service = get_faq_from_service(sentence,
                                                      service, history=[])  # add assertion here

        print(score, answer)
