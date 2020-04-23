import os
import time
import logging
import sqlite3
import asyncio
import subprocess
from datetime import timedelta

from spider import main


def create_project_logger():
    logger = logging.getLogger('mikan')
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler('mikan.log')
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
            '%(asctime)s %(name)s %(funcName)s [%(levelname)s]\n%(message)s\n',
            datefmt='%Y/%m/%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


LOGGER = create_project_logger()


def set_up():
    if not os.path.exists('img'):
        os.mkdir('img')
        LOGGER.info('mkdir: img')
    if not os.path.exists('torrent'):
        os.mkdir('torrent')
        LOGGER.info('mkdir: torrent')
    connection = sqlite3.connect('mikan.db')
    connection.execute(
            '''CREATE TABLE IF NOT EXISTS mikan_home
            (weekday, anime_id UNIQUE, background_image_src, last_update_date, anime_title)
            ''')
    connection.execute(
            '''CREATE TABLE IF NOT EXISTS anime_resource_info
            (publish_group_id, publish_group_name, resource_name UNIQUE, magnet_link,
            resource_size, publish_date, torrent_href, anime_id)
            ''')
    connection.close()


def disk_cleanup():
    stdout = subprocess.run(
            ['du', '-s', 'img', 'torrent'],
            capture_output=True,
            encoding='utf-8'
    ).stdout.strip()
    size1, size2 = stdout.split('\n')
    size = int(size1.split()[0]) + int(size2.split()[0])
    LOGGER.info(f'disk usage: {size / 1024:.2f} Mb.')
    if size > 1024 * 1024:
        remove_files('img')
        remove_files('torrent')


def remove_files(dir_name):
    now = time.time()
    timedelta0 = timedelta(days=100)
    for file in os.listdir(dir_name):
        file = os.path.join(dir_name, file)
        ctime = os.stat(file).st_ctime
        timedelta1 = timedelta(seconds=now - ctime)
        if timedelta1 > timedelta0:
            os.remove(file)
            LOGGER.info(f'Removed file: {file}.')


if __name__ == '__main__':
    begin = time.time()
    LOGGER.info('mikan spider starts running...')
    set_up()
    disk_cleanup()
    asyncio.run(main())
    end = time.time()
    seconds = timedelta(seconds=end - begin).total_seconds()
    LOGGER.info(f'all tasks are done, spend {seconds:.2f} seconds.\n')
    LOGGER.info('*' * 50 + '\n')
