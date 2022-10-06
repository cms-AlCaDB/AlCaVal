import os
import requests
from core_lib.utils.global_config import Config 
from requests import Session
from urllib.parse import urljoin

# Use requests module ignoring baseUrl 
# https://github.com/psf/requests/issues/2554#issuecomment-109341010
class LiveServerSession(Session):
    def __init__(self, prefix_url):
        self.prefix_url = prefix_url
        super(LiveServerSession, self).__init__()

    def request(self, method, url, *args, **kwargs):
        url = urljoin(self.prefix_url, url)
        return super(LiveServerSession, self).request(method, url, *args, **kwargs)
config = Config.load('config.cfg', os.getenv('INSTANCE', 'prod'))
askfor = LiveServerSession('http://{}:{}'.format(config.get('host'), config.get('port')))

# Use dictionary as object 
# https://joelmccune.com/python-dictionary-as-object/
class DictObj:
    def __init__(self, in_dict:dict):
        assert isinstance(in_dict, dict)
        for key, val in in_dict.items():
            if isinstance(val, (list, tuple)):
               setattr(self, key, [DictObj(x) if isinstance(x, dict) else x for x in val])
            else:
               setattr(self, key, DictObj(val) if isinstance(val, dict) else val)

    def get(self, attr):
        return getattr(self, str(attr))


def check_if_dataset_exists(urlpart):
    """Verify if dataset file exists in cmsweb dev instance"""
    grid_cert = Config.get('grid_user_cert')
    grid_key = Config.get('grid_user_key')
    url = 'https://cmsweb.cern.ch/dqm/dev/data/browse/ROOT/RelValData/'
    url += urlpart
    ret = requests.head(url, cert=(grid_cert, grid_key), verify=False)
    if ret.status_code != 200:
        return False
    else:
        return True
