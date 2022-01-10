import json
import random
from typing import Dict, List, Optional, Set, Tuple, Union, final

import codefast as cf
from authc import authc
from codefast.patterns.singleton import SingletonMeta

from rss.keys import BLOG_SOURCES, REDIS_MAP, TELEGRAM
from rss.redis import RedisClient
from rss.telegram import Telegram
from rss.urlparser import TextBody, UrlParser


class AuthOnce(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._info = {}

    def info(self):
        if not self._info:
            self._info = authc()
        return self._info


class Initiator(object):
    @staticmethod
    def redis():
        try:
            auth = AuthOnce().info()
            m = REDIS_MAP
            host, port, passwd = m['host'], m['port'], m['pass']
            return RedisClient(auth[host], auth[port], auth[passwd])
        except KeyError:
            cf.error('Authentication failed {}'.format(auth))
            return None
        except Exception as e:
            cf.error('Redis connection failed', str(e))
            return None


class BlogTracker(object):
    def __init__(self, parser: UrlParser):
        self.parser = parser
        self.redis = Initiator.redis()

    def _query_new(self) -> Dict:
        soup = self.parser.fetch_soup()
        results = self.parser.parse(soup)
        return dict((key, value.dict()) for key, value in results.items())

    def _query_old(self) -> Dict:
        return json.loads(self.redis.get_key('rss_{}'.format(
            self.parser.name)))

    def _query_digest(self, old: Dict, new: Dict) -> List[Tuple]:
        # Get to be posted contents.
        diff = new.keys() - old.keys()
        if not diff:
            return random.sample([(k, v) for k, v in new.items()], 1)
        redis_key = 'rss_{}'.format(self.parser.name)
        cf.info('found new blog', str(diff))
        cf.info('results stored in redis', redis_key)
        self.redis.set_key(redis_key, json.dumps(new), ex=86400 * 30)
        return [(key, new[key]) for key in diff]

    def track(self) -> List[Dict]:
        q_new = self._query_new()
        q_old = self._query_old()
        digest = self._query_digest(q_old, q_new)
        return [d[1] for d in digest]

    def format(self, dict_: Dict) -> str:
        tb = TextBody(**dict_)
        return str(tb)


class TelegramChannelPoster:
    def __init__(self, bot_name: str, channel_name: str):
        self.bot_name = bot_name
        self.channel_name = channel_name

    def post(self, msg: str) -> bool:
        auth = AuthOnce().info()
        bot = auth[self.bot_name]
        channel = auth[self.channel_name]
        resp = Telegram.post_to_channel(bot, channel, msg)
        if resp.status_code == 200:
            cf.info("message {} SUCCESSFULLY posted to {}".format(
                msg, channel))
            return True
        cf.error("message {} posting to {} failed".format(msg, channel))
        cf.error(resp)
        return False


def main():
    tcp = TelegramChannelPoster(TELEGRAM['bot_name'], TELEGRAM['channel_name'])
    for _, v in BLOG_SOURCES.items():
        parser = v['parser'](v['host'], v['url'])
        bt = BlogTracker(parser)
        for digest in bt.track():
            tcp.post(bt.format(digest))
