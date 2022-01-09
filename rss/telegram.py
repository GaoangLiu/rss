import codefast as cf
import requests
from authc import authc


class Telegram(object):
    @staticmethod
    def post_to_channel(bot: str,
                        channel: str,
                        msg: str,
                        timeout: int = 60) -> bool:
        cf.info('posting {} to channel {}'.format(msg, channel))
        url = "https://api.telegram.org/bot{}/sendMessage?chat_id=@{}&text={}".format(
            bot, channel, msg)
        resp = requests.get(url, timeout=timeout)
        return resp
