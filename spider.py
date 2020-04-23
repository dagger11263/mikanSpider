import os
import logging
import sqlite3
import asyncio
from functools import partial
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup
from requests import session
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException

TIMEOUT = 10
MAX_THREADS = 128
MIKAN_HOME = 'https://mikanani.me'
LOGGER = logging.getLogger('mikan.spider')
EXECUTOR = ThreadPoolExecutor(max_workers=MAX_THREADS)
DATABASE_CONNECTION = sqlite3.connect('mikan.db')


def get_session():
    _session = session()
    adapter = HTTPAdapter(pool_maxsize=MAX_THREADS, max_retries=3)
    _session.mount('https://', adapter)
    return _session


SESSION = get_session()
curl = partial(SESSION.get, timeout=TIMEOUT)


def save_mikan_home(tag):
    data = []
    weekday = tag['data-dayofweek']
    LOGGER.debug(f'weekday: {weekday}')
    anime_id, background_image_src, last_update_date, anime_title = '', '', '', ''
    for li in tag.find_all('li'):
        for child in li.children:
            if child.name == 'span':
                anime_id = child['data-bangumiid']
                background_image_src = child['data-src']
                LOGGER.debug(f'anime_id: {anime_id}, background_image_src: {background_image_src}')
            elif child.name == 'div':
                text = child.get_text('\t', strip=True)
                if text.startswith('2020') or text.startswith('此番组下暂无作品'):
                    last_update_date, anime_title = text.split('\t')
                    LOGGER.debug(f'last_update_date: {last_update_date}, anime_title: {anime_title}')
        data.append([weekday, anime_id, background_image_src, last_update_date, anime_title])

    try:
        DATABASE_CONNECTION.executemany('INSERT OR REPLACE INTO mikan_home VALUES(?,?,?,?,?)', data)
    except sqlite3.IntegrityError as e:
        LOGGER.error(str(e))


def crawl_mikan_home():
    try:
        response = curl(MIKAN_HOME)
    except RequestException as e:
        LOGGER.critical(f'crawl mikan home failed: {e} please check your network.')
        raise e
    LOGGER.info(f'{MIKAN_HOME} response status code: {response.status_code}')
    soup = BeautifulSoup(response.text, 'html.parser')
    for tag in soup.find_all('div', class_='sk-bangumi'):
        save_mikan_home(tag)


def save_anime_resource_info(tags, anime_id):
    data = []
    publish_group_id, publish_group_name = '', ''
    for t in tags:
        if t.name == 'div':
            publish_group_id = t['id']
            LOGGER.debug(f'publish_group_id: {publish_group_id}')
            if publish_group_id == '202':
                publish_group_name = next(t.strings).strip()
            else:
                publish_group_name = t.a.string
            LOGGER.debug(f'publish_group_name: {publish_group_name}')
            continue

        children = t.find_all('td')
        resource_name = children[0].a.string
        magnet_link = children[0].a.next_sibling.next_sibling['data-clipboard-text']
        resource_size = children[1].string
        publish_date = children[2].string
        torrent_href = children[3].a['href']
        resource_info = [
            publish_group_id,
            publish_group_name,
            resource_name,
            magnet_link,
            resource_size,
            publish_date,
            torrent_href,
            anime_id
        ]
        LOGGER.debug(f'resource_info: {resource_info}')
        data.append(resource_info)

    try:
        DATABASE_CONNECTION.executemany(
                'INSERT OR IGNORE INTO anime_resource_info VALUES (?,?,?,?,?,?,?,?)',
                data
        )
    except sqlite3.IntegrityError as e:
        LOGGER.error(str(e))


async def crawl_anime_resource_info(anime_id):
    resource_url = MIKAN_HOME + '/Home/Bangumi/' + anime_id
    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(EXECUTOR, curl, resource_url)
    except RequestException as e:
        LOGGER.error(f'crawl anime_{anime_id} resource info failed: {e}')
        return
    soup = BeautifulSoup(response.text, 'html.parser')
    tags = soup.select('div .subgroup-text, tbody > tr')
    save_anime_resource_info(tags, anime_id)


def get_task_save_path(url, dir_name):
    parts = url.split('/')
    basename = parts[-2] + '_' + parts[-1]
    return os.path.join(dir_name, basename)


async def download_task(url, path):
    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(EXECUTOR, curl, url)
    except RequestException as e:
        LOGGER.error(f'download {url} failed: {e}')
        return
    with open(path, 'wb') as f:
        f.write(response.content)


async def main():
    try:
        crawl_mikan_home()
    except RequestException:
        return

    loop = asyncio.get_running_loop()
    tasks = []
    anime_ids = [row[0] for row in DATABASE_CONNECTION.execute(
            'SELECT anime_id FROM mikan_home'
    )]
    while anime_ids:
        tasks.append(loop.create_task(crawl_anime_resource_info(anime_ids.pop())))
    LOGGER.info(f'{len(tasks)} crawl anime resource info tasks start.')
    await asyncio.wait(tasks)
    tasks.clear()

    background_image_sources = [row[0] for row in DATABASE_CONNECTION.execute(
            'SELECT background_image_src FROM mikan_home'
    )]
    while background_image_sources:
        url = MIKAN_HOME + background_image_sources.pop()
        path = get_task_save_path(url, 'img')
        if not os.path.exists(path):
            tasks.append(loop.create_task(download_task(url, path)))
    LOGGER.info(f'{len(tasks)} download tasks start.')
    if tasks:
        await asyncio.wait(tasks)
        tasks.clear()

    torrent_references = [row[0] for row in DATABASE_CONNECTION.execute(
            'SELECT torrent_href FROM anime_resource_info'
    )]
    while torrent_references:
        url = MIKAN_HOME + torrent_references.pop()
        path = get_task_save_path(url, 'torrent')
        if not os.path.exists(path):
            tasks.append(loop.create_task(download_task(url, path)))
    LOGGER.info(f'{len(tasks)} download tasks start.')
    if tasks:
        await asyncio.wait(tasks)

    DATABASE_CONNECTION.commit()
    DATABASE_CONNECTION.close()
