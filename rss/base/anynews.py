import json
import codefast as cf
from abc import ABC, abstractmethod
from typing import List, NamedTuple, Tuple
from bs4 import BeautifulSoup
from codefast.functools import naruto
from rss.core import Initiator, Spider, shorten_url


class Article(NamedTuple):
    uid: str = None
    title: str = None
    url: str = None
    source: str = None
    author: str = None
    date: str = None
    extra_url: str = None

    def __str__(self):
        return '\n'.join(
            ['{}: {}'.format(k, v) for k, v in self._asdict().items() if v])

    def telegram_format(self) -> str:
        short_url = shorten_url(self.url)
        msg = 'Title: {}\nURL: {}'.format(self.title, short_url)
        if self.source:
            msg += '\nSource: {}'.format(self.source)
        return msg


class DummyItem(NamedTuple):
    text: str = ''
    href: str = ''


class AnyNews(ABC):
    """ check whether any new articles posted in a certain website
    """
    def __init__(self, main_url: str):
        self.main_url = main_url
        self.spider = Spider().born()
        self.type = 'anynews'
        self._redis = None
        self._archives = None

    @property
    def redis(self):
        if not self._redis:
            self._redis = Initiator.redis()
        return self._redis

    @property
    def archives(self):
        if not self._archives:
            self._archives = self.get_archives()
        cf.info('found archives {} \nfor key {}'.format(
            self._archives, self.type))
        return self._archives

    def get_soup(self) -> BeautifulSoup:
        soup = self.spider.get(self.main_url)
        return BeautifulSoup(soup.content, 'html.parser')

    @abstractmethod
    def search_articles(self, soup: BeautifulSoup) -> List[Article]:
        pass

    def latest(self, new: List[Article]) -> List[Article]:
        # Return the latest articles list
        return [e for e in new if not self.redis.exists(e.uid)]

    def get_archives(self) -> List[Article]:
        return []

    def save_to_redis(self, articles: List[Article]) -> bool:
        for art in articles:
            self.redis.set_key(art.uid, 1, ex=864000)
        return True

    def pipeline(self) -> List[Article]:
        soup = self.get_soup()
        articles = self.search_articles(soup)
        articles = self.latest(articles)
        return articles
