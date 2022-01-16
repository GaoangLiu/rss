import base64
import concurrent.futures
import time
from typing import List

from rss.base import AnyNews, Article
from rss.data import WECHAT_PUBLIC


class WechatPublic(AnyNews):
    # wechat public articles base class
    def __init__(self, main_url, source: str = ''):
        super().__init__(main_url)
        self.source = source  # 公众号名称

    def get_wechat_url(self, url: str, retry: int = 20) -> str:
        retry = retry
        while retry >= 0 and 'mp.weixin.qq.com' not in url:
            retry -= 1
            url = self.spider.get(url).url
            time.sleep(0.5)
        return url

    def search_articles(self, soup) -> List[Article]:
        articles, wechat_urls = [], []

        for div in soup.find_all('div', class_='title'):
            href = div.find('a') or {}
            href = href.get('href')
            if href:
                wechat_urls.append(href)
                title = div.text.replace('原创', '').strip()
                article = Article(title=title, source=self.source)
                articles.append(article)

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            tasks = [
                executor.submit(self.get_wechat_url, url)
                for url in wechat_urls
            ]
            for i, task in enumerate(concurrent.futures.as_completed(tasks)):
                url = task.result()
                unique_id = base64.b64encode(
                    articles[i].title.encode('utf-8')).decode('utf-8')
                articles[i] = Article(title=articles[i].title,
                                      uid=unique_id,
                                      source=self.source,
                                      url=url)
        return articles


def worker_factory(main_url: str, source, redis_subkey: str) -> WechatPublic:
    wp = WechatPublic(main_url, source)
    wp.type += ':%s' % redis_subkey
    return wp


def create_rss_worker(key: str) -> WechatPublic:
    map_ = WECHAT_PUBLIC[key]
    return worker_factory(map_['main_url'], map_['source'],
                          map_['redis_subkey'])
