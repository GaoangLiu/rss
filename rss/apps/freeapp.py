#!/usr/bin/env python
import hashlib
from email import message
from hmac import digest
from typing import NamedTuple

import codefast as cf
import feedparser
from authc import get_redis
from bs4 import BeautifulSoup
from dofast.cell.api import API

from rss.apps.bark import BarkErrorAlert


class FeedBody(NamedTuple):
    title: str
    download_url: str
    date: str
    preview: str
    image: str

    def is_complete(self) -> bool:
        return all(field is not None for field in self)

    def tweets_format(self) -> str:
        return '{}\n\n{}\n\n下载链接: {}\n#iOS限免'.format(self.title, self.preview,
                                                     self.download_url)

    def __repr__(self) -> str:
        return '\n'.join(
            ['{:<20}: {}'.format(k, v) for k, v in self._asdict().items()])


class FreeApp(object):
    def __init__(self) -> None:
        self.url = 'http://free.apprcn.com/category/ios/feed/'

    def get_feeds(self):
        feeds = feedparser.parse(self.url)
        feed_list = []
        for e in feeds['entries']:
            title, download_url, date, preview, image = e['title'], None, e[
                'published'], None, None
            if 'content' in e:
                soup = BeautifulSoup(e['content'][0]['value'], 'html.parser')
                preview = next((p.text for p in soup.find_all('p') if p.text),
                               None)
                for a in soup.findAll('a'):
                    if 'apps.apple.com' in a.attrs.get('href', ''):
                        download_url = a.attrs['href']
                        break
                for img in soup.findAll('img'):
                    if 'freeapp.macapp8.com' in img.attrs.get('src', ''):
                        image = img.attrs['src']
                        break

                feedbody = FeedBody(title=title,
                                    download_url=download_url,
                                    date=date,
                                    preview=preview,
                                    image=image)
                cf.info('feedbody is', feedbody)
                cf.info('is complete ?', feedbody.is_complete())
                if feedbody.is_complete():
                    feed_list.append(feedbody)
        return feed_list


class Worker(object):
    def __init__(self) -> None:
        self.feeder = FreeApp()
        self.redis = get_redis()
        self.api = API()

    def is_feed_new(self, feed) -> bool:
        digest = hashlib.sha256(str(feed).encode()).hexdigest()
        cf.info('digest is', digest)
        if self.redis.exists(digest):
            return False
        self.redis.set(digest, 1, ex=86400 * 15)
        return True

    def post_tweets(self):
        for feed in self.feeder.get_feeds():
            if self.is_feed_new(feed):
                try:
                    self.api.twitter.post([feed.tweets_format()])
                    cf.info('posting feed \n{}'.format(feed.tweets_format()))
                    return
                except Exception as e:
                    BarkErrorAlert(title='FREEAPP推送失败', message=str(e)).send()
                    cf.error('posting feed failed', e)


def publish_feeds():
    worker = Worker()
    worker.post_tweets()
