import requests
import os
import codefast as cf


class BarkErrorAlert(object):
    def __init__(self, title: str, message: str) -> None:
        self.barkhost = cf.io.reads(
            os.path.expanduser('~/.config/barkhost')).rstrip()
        self.icon = 'https://s3.bmp.ovh/imgs/2022/04/13/9b774ff9ca72aea3.png'
        self.title = title
        self.message = message

    def send(self):
        try:
            path = cf.urljoin(
                self.barkhost, '/{}/{}?icon={}'.format(self.title, self.message, self.icon))
            path = path.replace(' ', '%20')
            requests.post(path)
        except Exception as e:
            cf.error(str(self.__class__.__name__) + ': ' + str(e))


class ErrorAlert(object):
    @classmethod
    def send(cls, title: str, message: str):
        BarkErrorAlert(title, message).send()
