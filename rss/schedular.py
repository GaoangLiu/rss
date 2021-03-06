from sched import scheduler
import socket
import threading
import time
from enum import Enum

import codefast as cf
from apscheduler.schedulers.background import BackgroundScheduler

from rss.apps.freeapp import publish_feeds
from rss.apps.huggingface import HuggingFace
from rss.apps.leiphone import LeiPhoneAI
from rss.apps.rust import RustLangDoc
from rss.base.wechat_public import create_rss_worker
from rss.base.wechat_rss import create_rss_worker as create_wechat_rss_worker
from rss.core.tg import tcp, post_tweet
from rss.tracker import main as blog_main
from ojbk import report_self

socket.setdefaulttimeout(300)


class PostType(str, Enum):
    """
    PostType
    """
    IMMEDIATE = 'immediate'
    EVENING8 = 'evening8'


class Schedular(object):
    def __init__(self):
        """Add disturb to avoid multiple updates posted at exactly the same time
        Args:
            post_type(PostType): whether to post immediately or delay at a certain time, e.g., 20:00 pm
        """
        self.timer = 0
        self.articles_stack = []

    def run(self):
        cf.info("schedular: %s is running" % self.__class__.__name__)
        self.action()

    def run_worker(self, worker):
        latest = worker.pipeline()
        if not latest:
            cf.info('no new articles for {}'.format(worker.__class__.__name__))
        else:
            worker.save_to_redis(latest)
            cf.info('all articles saved to redis')
            self.articles_stack = []
            for article in latest:
                cf.info(article)
                tcp.post(article.telegram_format())


class DailyBlogTracker(Schedular):
    def __init__(self):
        super().__init__()

    def action(self):
        cf.info("DailyBlogTracker is running")
        blog_main()


class LeiPhoneAIRss(Schedular):
    def action(self):
        self.run_worker(LeiPhoneAI())


class HuggingFaceRss(Schedular):
    def action(self):
        self.run_worker(HuggingFace())


class RustLanguageDoc(Schedular):
    def action(self):
        self.run_worker(RustLangDoc())


class WechatPublicRss(Schedular):
    def __init__(self, wechat_id: str = 'almosthuman'):
        super().__init__()
        self.worker = create_rss_worker(wechat_id)

    def action(self):
        self.run_worker(self.worker)


class WechatRssMonitor(Schedular):
    def __init__(self, wechat_id: str = 'almosthuman'):
        super().__init__()
        self.worker = create_wechat_rss_worker(wechat_id)

    def action(self):
        self.run_worker(self.worker)


class SchedularManager(object):
    def __init__(self):
        self.schedulars = []
        self.timer = 0

    def add_schedular(self, schedular) -> Schedular:
        self.schedulars.append(schedular)
        return self

    def run_once(self):
        for schedular in self.schedulars:
            try:
                threading.Thread(target=schedular.run).start()
            except Exception as e:
                cf.error('shcedular {} error: {}'.format(schedular, e))

    def run(self):
        cf.info('schedular manager is running')
        self.run_once()


def rsspy():
    manager = SchedularManager()
    manager.add_schedular(LeiPhoneAIRss())
    manager.add_schedular(HuggingFaceRss())
    # manager.add_schedular(DailyBlogTracker())
    manager.add_schedular(WechatPublicRss(wechat_id='huxiu'))

    wechat_ids = [
        'almosthuman', 'yuntoutiao', 'aifront', 'rgznnds', 'infoq', 'geekpark',
        'qqtech'
    ]
    for wechat_id in wechat_ids:
        manager.add_schedular(WechatRssMonitor(wechat_id))

    try:
        manager.run()
        report_self('RSS')
    except Exception as e:
        from rss.apps.bark import ErrorAlert
        ErrorAlert.send(title="RSSPY RUN FAILURE", message=str(e))
        cf.error('rsspy run failure', e)


if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=publish_feeds, trigger='interval', seconds=60)
    scheduler.add_job(func=rsspy,
                      trigger='cron',
                      hour="8-20",
                      minute='*/7',
                      timezone='Asia/Shanghai')
    scheduler.start()
    cf.info('rss scheduler started')
    while True:
        time.sleep(1)
