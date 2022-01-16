import codefast as cf
from rss.apps.tg import tcp
import time
from rss.tracker import main as blog_main
from rss.base.wechat_public import create_rss_worker
from rss.apps.leiphone import LeiPhoneAI


class Schedular(object):
    def __init__(self, shift_time: int = 3600):
        self.shift_time = shift_time
        self.timer = 0

    def run(self):
        self.timer += 1
        if self.timer % self.shift_time == 0:
            cf.info("Schedular: %s is running" % self.__class__.__name__)
            self.timer = 0
            self.action()


class DailyBlogTracker(Schedular):
    def __init__(self, shift_time: int = 3600 * 24):
        super().__init__(shift_time=shift_time)

    def action(self):
        cf.info("DailyBlogTracker is running")
        blog_main()


class LeiPhoneAIRss(Schedular):
    def action(self):

        worker = LeiPhoneAI()
        latest, all_ = worker.pipeline()
        latest = all_[0:1]
        if not latest:
            cf.info('No new articles')
            return

        worker.save_to_redis(all_)
        cf.info('all articles saved to redis')
        for article in latest:
            cf.info(article)
            tcp.post(article.telegram_format())


class WechatPublicRss(Schedular):
    def __init__(self, shift_time: int = 3600, wechat_id: str = 'almosthuman'):
        super().__init__(shift_time=shift_time)
        self.worker = create_rss_worker(wechat_id)

    def action(self):
        latest, all_ = self.worker.pipeline()
        if not latest:
            cf.info('no new articles')
            tcp.post(all_[0].telegram_format())
            exit(0)

        self.worker.save_to_redis(all_)
        cf.info('all articles saved to redis')

        for article in latest:
            cf.info(article.telegram_format())
            # tcp.post(article.telegram_format())

        # tcp.post(latest[0].telegram_format())
        exit(0)


class SchedularManager(object):
    def __init__(self):
        self.schedulars = []

    def add_schedular(self, schedular):
        self.schedulars.append(schedular)

    def run(self):
        while True:
            for schedular in self.schedulars:
                schedular.run()
            time.sleep(1)


if __name__ == '__main__':
    sm = SchedularManager()
    # sm.add_schedular(WechatPublicRss(shift_time=3, wechat_id='almosthuman'))
    sm.add_schedular(WechatPublicRss(shift_time=3, wechat_id='aifront'))
    # sm.add_schedular(LeiPhoneAIRss(shift_time=3))
    # sm.add_schedular(DailyBlogTracker(shift_time=3600 * 24))
    sm.run()