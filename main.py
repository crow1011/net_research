import asyncio
import aiohttp
from time import time, sleep
import hashlib
from elasticsearch import Elasticsearch, ConnectionError

print('START')

query_interval = 15
es = Elasticsearch(hosts='http://es:9200')


def gen_addrs():
    urls = ['https://google.com', 'https://python.org', 'https://stackoverflow.com', 'https://httpbin.org']
    for url in urls:
        yield url


async def to_es(report):
    es.index(
        index="net_research",
        id=report['host'],
        body=report,
    )


async def fetch_content(url, session):
    report = {}
    async with session.get(url, allow_redirects=True) as response:
        data = await response.read()
        report['host'] = url
        report['hdata'] = hashlib.md5(data).hexdigest()
        report['status'] = response.status
        report['headers'] = dict(response.headers)
        # await to_es(report)
        await to_es(report)


async def main():
    # вместо списка urls может быть генератор отдающий по одному адреса
    # не стал использовать ip-адреса, так как не понял как обойти пролему с dns \
    # в случаях когда за одним адресом находится несколько ресурсов
    # по логике там фронт просто заглушку покажет
    urls = gen_addrs()
    tasks = []
    async with aiohttp.ClientSession() as session:
        for url in urls:
            task = asyncio.create_task(fetch_content(url, session))
            tasks.append(task)

        await asyncio.gather(*tasks)


if __name__ == '__main__':
    while True:
        try:
            t0 = time()
            asyncio.run(main())
            print('Last scan time:', time() - t0)
        except ConnectionError:
            print('Elasticsearch is not ready')
        except Exception as e:
            print('EGOR:')
            print(e)
        sleep(query_interval)
