import json
import random
from typing import Dict, List, Optional, Set, Tuple, Union

import codefast as cf
from authc import authc

from rss.keys import OBSERVE_MAP, REDIS_MAP
from rss.openai import OpenAI
from rss.redis import RedisClient
from rss.telegram import Telegram
from rss.tensorflow import TensorFlowBlog
from rss.urlparser import TextBody


class Observer(object):
    def __init__(self):
        auth = authc()
        if not auth:
            cf.error('Authentication failed {}'.format(auth))
        else:
            m = REDIS_MAP
            host, port, passwd = m['host'], m['port'], m['pass']
            self.redis = RedisClient(auth[host], auth[port], auth[passwd])

    def observe(self, observe_key: str) -> List[Dict]:
        """ Return a list of newly posted blogs, or sample 3 if no new blogs were found.
        """
        observer = OBSERVE_MAP[observe_key]
        cli = observer['parser'](observer['host'], observer['url'])
        soup = cli.fetch_soup()
        results = cli.parse(soup)
        results = dict((key, value.json()) for key, value in results.items())

        cf.info('observed', str(cli))
        redis_key = 'rss_' + observe_key
        previouse_results = json.loads(self.redis.get_key(redis_key))
        cf.info('previous results loaded')

        diff = results.keys() - previouse_results.keys()
        if diff:
            cf.info('found new blog', str(diff))
            cf.info('results stored in redis', redis_key)
            self.redis.set_key(redis_key, json.dumps(results), ex=86400 * 30)
            return [(key, results[key]) for key in diff]
        return random.sample([(k, v) for k, v in results.items()], 1)

    def format(self, dict_: Dict) -> str:
        tb = TextBody(**dict_)
        return str(tb)


class EntryPoint:
    def __init__(self):
        self._auth = None

    @property
    def auth(self):
        if not self._auth:
            self._auth = authc()
        return self._auth

    def post(self, msg: str):
        bot = self.auth['hema_bot']
        channel = self.auth['global_news_podcast']
        resp = Telegram.post_to_channel(bot, channel, msg)
        if resp.status_code == 200:
            cf.info("message {} SUCCESSFULLY posted to {}".format(
                msg, channel))
            return True
        cf.error("message {} posting to {} failed".format(msg, channel))
        cf.error(resp)
        return False


def main():
    obs = Observer()
    observee = ['openai', 'tensorflow']
    ep = EntryPoint()
    for key in observee:
        resp = obs.observe(key)
        for _, value in resp:
            dict_ = json.loads(value)
            msg = obs.format(dict_)
            ep.post(msg)
