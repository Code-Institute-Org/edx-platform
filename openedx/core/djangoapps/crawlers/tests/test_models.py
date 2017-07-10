# -*- coding: utf-8 -*-
"""
Tests that the request came from a crawler or not.
"""
import unittest
import ddt
from django.http import HttpRequest
from openedx.core.djangoapps.crawlers.models import CrawlersConfig


@ddt.ddt
class CrawlersConfigTest(unittest.TestCase):

    @ddt.data(
        "Mozilla/5.0 (Linux; Android 5.1; Nexus 5 Build/LMY47I; wv) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Version/4.0 Chrome/47.0.2526.100 Mobile Safari/537.36 edX/org.edx.mobile/2.0.0",
        "Le Héros des Deux Mondes",
    )
    def test_req_user_agent_is_not_crawler(self, req_user_agent):
        """
        verify that the request did not come from a crawler.
        """
        CrawlersConfig.objects.create(known_user_agents='edX-downloader,crawler_foo', enabled=True)
        fake_request = HttpRequest()
        fake_request.META['HTTP_USER_AGENT'] = req_user_agent
        self.assertFalse(CrawlersConfig.is_crawler(fake_request))

    @ddt.data(
        u"edX-downloader",
        "crawler_foo".encode("utf-8")
    )
    def test_req_user_agent_is_crawler(self, req_user_agent):
        """
        verify that the request came from a crawler.
        """
        CrawlersConfig.objects.create(known_user_agents='edX-downloader,crawler_foo', enabled=True)
        fake_request = HttpRequest()
        fake_request.META['HTTP_USER_AGENT'] = req_user_agent
        self.assertTrue(CrawlersConfig.is_crawler(fake_request))
