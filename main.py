# -*- coding: utf-8 -*-

"""
Это набросок реального сервиса, который возможно получится запустить
Идея такая: повесить на фон службу, которая будет собирать инфу с пула адресов или всего интернета
Собранные данные будут сливаться в elasticsearch и обновляться там через промежутки времени
в Kibana можно проводить полнотекстовый поиск по headers и тд.
сам elastic может выступать источником данных для mp siem? ptaf?
После elastic можно сделать службу, которая будет в него смотреть и проводить аналитику автоматическую
какую аналитику пока не знаю
Мультипоточность и мультипроценнсинг не решился применять, тестовые скрипты не сильно быстрее работают,
надо еще копать
"""

import asyncio
import aiohttp
from time import time, sleep
import hashlib
from elasticsearch import Elasticsearch, ConnectionError

# метка старта скрипта
# обычно пишу логи в отдельный файл с помощью logging, но на одном собесе посоветовали в случае использования \
# docker писать в stdout, легче снимать логи и для k8s легче перебрасывать контейнер между нодами
print('START')
# задает интервал между запусками сбора данных
query_interval = 15
# создает коннектор к elasticsearch
es = Elasticsearch(hosts='http://es:9200')


def gen_addrs():
    # генератор возвращает по одному адресу за шаг
    urls = ['https://google.com', 'https://python.org', 'https://stackoverflow.com', 'https://httpbin.org']
    for url in urls:
        yield url


async def to_es(report):
    # отправляет в elasticsearch report
    # в качестве id документа используется url, это позволяет обновлять данные по каждому url, \
    # а не записывать новые копии. Полезно для уменьшения объема данных
    # если нужно мониторить изменения в данных url, можно убрать параметр id
    es.index(
        index="net_research",
        id=report['host'],
        body=report,
    )


async def fetch_content(url, session):
    report = {}
    async with session.get(url, allow_redirects=True) as response:
        data = await response.read()
        # собирает report, набор данных взял номинальный
        report['host'] = url
        # хэш содержимого страницы, чтобы не писать все в elastic
        report['hdata'] = hashlib.md5(data).hexdigest()
        report['status'] = response.status
        report['headers'] = dict(response.headers)
        # отправка в elasticsearch
        await to_es(report)


async def main():
    # не стал использовать ip-адреса, так как не понял как обойти пролему с dns \
    # в случаях когда за одним адресом находится несколько ресурсов
    # по логике там фронт просто заглушку покажет
    urls = gen_addrs()
    # очередь для тасков
    tasks = []
    async with aiohttp.ClientSession() as session:
        # набиваем очередь тасками в рамках одной сесси
        for url in urls:
            task = asyncio.create_task(fetch_content(url, session))
            tasks.append(task)
        # распаковывам список тасков для запуска
        await asyncio.gather(*tasks)


if __name__ == '__main__':
    while True:
        try:
            t0 = time()
            asyncio.run(main())
            print('Last scan time:', time() - t0)
        except ConnectionError:
            # одно из решений проблемы, когда контейнер с elastic поднялся, но подключения принимать не готов
            print('Elasticsearch is not ready')
        except Exception as e:
            print('EGOR:')
            print(e)
        sleep(query_interval)
