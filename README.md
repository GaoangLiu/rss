A simple blog, with topics retricted to NLP & ML, urls generator. 

Supported sites include:
- https://openai.com
- https://blog.tensorflow.org
- https://tech.meituan.com

Blog titles, links and dates will be parsed out and cached into redis. Daily digests are issued through (personal) Telegram channel.

This repo is also packed up and posted on [https://pypi.org](https://pypi.org/project/rsspy/) as a Python3 library. 
- Install by running `pip3 install rsspy`. 
- Dependations: `codefast` (for logging), `authc` (for authentication of redis/Telegram accounts), `redis` (for caching results).


