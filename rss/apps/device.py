import codefast as cf
import requests


class DeviceInfo(object):
    def collect(self):
        self.hostname = cf.shell('hostname')
        self.ip = requests.get('http://ipinfo.io/ip').text.strip()

    def __str__(self) -> str:
        self.collect()
        return '%s, %s' % (self.hostname, self.ip)
