"""
Поиск страниц на AnimeNewsNetwork и их обработка.
"""
import xml.etree.ElementTree as et
from time import sleep
import requests
import dateutil.parser as date_parser
from PIL import Image
from urllib.request import urlopen

import db
from constants import *


def number_of_volumes(ann_xml: str) -> int | bool:
    """
    Поиск количества томов манги на ANN.
    :param ann_xml: XML-страница манги на ANN.
    :return: Количество томов манги. Если нет соответствующего поля, — False.
    """
    # root = et.fromstring(ann_xml)
    # for info in root[0].findall('info'):
    #     if info.get('type') == 'Number of tankoubon':
    #         return int(info.text)
    pos = ann_xml.find('Number of tankoubon') + 21
    if pos != 20:
        return int(ann_xml[pos:ann_xml.find('<', pos)])
    return False


def date_of_premiere_manga(ann_xml: str) -> str | bool:
    """
    Извлечение даты премьеры манги из ANN.
    :param ann_xml: XML-страница манги в ANN.
    :return: Дата премьеры или False.
    """
    pos1 = ann_xml.find('type="Vintage"') + 15
    date_of_premiere = ann_xml[pos1:pos1 + 10]
    dp = date_parser.parse(date_of_premiere).strftime('%Y-%m-%d')
    if dp != date_of_premiere:
        return False
    return date_of_premiere


def manga_pages(ann_page: str, ann_pages: dict) -> dict:
    """
    Поиск в ANN связанной манги, отсутствующей в World Art, и добавление в словарь ann_pages.
    :param ann_page: XML-страница манги в ANN.
    :param ann_pages: Словарь ANN-страниц манги (ann_pages = {ann_id: обработана?}).
    :return: Редактированный словарь ANN-страниц манги ann_pages.
    """
    pos1 = ann_page.find('<related-next id="') + 18
    if pos1 != 17:
        pose = ann_page.find('<info', pos1)
        while pos1 > 17:
            pos2 = ann_page.find('"', pos1, pose)
            ann_id = int(ann_page[pos1:pos2])
            if ann_page[pos2 + 7:pos2 + 17] == 'adaptation':
                pos1 = ann_page.find('<related-next id="', pos2 + 17, pose) + 18
            elif ann_id not in ann_pages:
                ann_pages[ann_id] = False
                pos1 = ann_page.find('<related-next id="', pos2, pose) + 18
    return ann_pages


def manga_from_anime(anime_page: str) -> str | bool:
    """
    Страница манги в ANN по связанному anime в ANN.
    :param anime_page: XML-страница anime в ANN.
    :return: XML-страница манги в ANN.
    """
    pos = anime_page.find('<related-prev rel="adapted from" id="') + 37
    if pos == 36:
        return False
    pos2 = anime_page.find('"/>', pos)
    mid = int(anime_page[pos:pos2])
    sleep(1)
    return requests.get(f'{CANNE}api.xml', {M: mid}).text


# def number_of_chapters(ann_page: str) -> int:
#     pass


def authors_of_manga_id(ann_xml: str, oam: str) -> list[int] | bool:
    """
    Поиск ID соответствующих авторов манги из ANN в БД.
    :param ann_xml: XML-страница.
    :param oam: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID авторов манги в БД, если найдены. Иначе — False.
    """
    staffs = ('<task>Story &amp; Art</task>', '<task>Story</task>', '<task>Original creator</task>', '<task>Art</task>')
    authors = []
    for staff in staffs:
        posa = 0
        while True:
            posa = ann_xml.find('<staff ', posa)
            if posa == -1:
                break
            posb = ann_xml.find('</staff>', posa)
            pos = ann_xml.find(staff, posa, posb)
            if pos == -1:
                posa = posb
                continue
            break
        if posa == -1:
            continue
        pos = ann_xml.find('<person id="', pos, posb) + 12
        pid = int(ann_xml[pos:ann_xml.find('"', pos, posb)])
        sleep(1)
        ann_page = requests.get(f'{SANNE}people.php', {'id': pid}).text
        pos = ann_page.find('<h1 id="page_header" class="same-width-as-main">') + 49
        pose = ann_page.find('</div>', pos)
        pos2 = ann_page.find('</h1>', pos, pose)
        name_rom_ = ann_page[pos:pos2].strip().split(' ')
        name_rom = name_rom_[1].lower().title() + ' ' + name_rom_[0]
        name_orig = ann_page[pos2 + 6:pose].strip()
        authors.append({'name_orig': name_orig, 'name_rom': name_rom, 'exist': False})
    return db.authors_of_manga_id(authors, oam)


def search_publishing(ann_id: int) -> str | bool:
    """
    Поиск и извлечение издательства из ANN.
    :param ann_id: ID страницы.
    :return: Наименование издательства или False.
    """
    def match():
        pos = data.find('">', pos1, pos2) + 2
        return data[pos:pos2]

    sleep(1)
    data = requests.get(f'{SANNE}{M}.php', {'id': ann_id}).text
    pos1 = data.find('<b>Publisher</b>')
    if pos1 == -1:
        return False
    pose = data.find('</div>', pos1)
    while True:
        pos1 = data.find('<a href="company.php', pos1, pose) + 20
        if pos1 == 19:
            return False
        pos2 = data.find('</a> <small>(', pos1, pose)
        if pos2 != -1:
            note = data[pos2:data.find(')', pos2 + 13, pose)]
            if 'serialization' in note:
                return match()
        else:
            pos2 = data.find('</a><br>', pos1, pose)
            return match()
        pos1 = pos2


def publications_id_and_date_of_premiere(ann_xml: str, oam: str, put_publication) -> tuple[list[int] | bool, str]:
    """
    Поиск ID соответствующих изданий из ANN в БД и извлечение даты премьеры.
    :param ann_xml: XML-страница.
    :param oam: Страница веб-приложения интерфейса БД (HTML-код).
    :param put_publication: Функция добавления издания в БД и возврата ID.
    :return: Список ID изданий в БД (или False) и дата премьеры.
    """
    pos1 = ann_xml.find('type="Vintage"') + 15
    pose = ann_xml.find('<staff ', pos1)
    date_of_premiere = date_of_premiere_manga(ann_xml)
    pos = ann_xml.find('serialized in ', pos1, pose) + 14
    if pos == 13:
        if not date_of_premiere:
            raise ValueError('В ANN нет ни издания, ни даты.')
        return False, date_of_premiere
    else:
        pos2 = ann_xml.find(', ', pos, pose)
        ann_publications = [{'name': ann_xml[pos:pos2], 'exist': False}]
    return db.publications_id(oam, ann_publications, put_publication), date_of_premiere


def title(ann_xml: str, lang: str) -> str:
    """
    Извлечение наименования из ANN.
    :param ann_xml: XML-страница.
    :param lang: Язык наименования: "orig", "eng".
    :return: Оригинальное наименование.
    """
    langs = {'orig': 'JA', 'eng': 'EN'}  # 'rus': 'RU'
    pos1 = 0
    while True:
        pos1 = ann_xml.find('type="Alternative title"', pos1)
        if pos1 == -1:
            return ''
        pos2 = ann_xml.find('</info>', pos1)
        pos1 = ann_xml.find(f'lang="{langs[lang]}"', pos1, pos2) + 10
        if pos1 != 9:
            return ann_xml[pos1:pos2]
        pos1 = pos2


def poster(page: str, mid: int, name: str) -> None:
    """
    Поиск, загрузка и сохранение постера манги с сервера ANN в виде миниатюрной картинки для своей БД.
    :param page: XML-страницы.
    :param mid: ID в БД (возвращённое db.put).
    :param name: Наименование.
    """
    page = et.fromstring(page)
    try:
        url = page[0].find('info').attrib['src']
    except Exception:
        with open(f'{PATH}m/report.log', 'a', encoding='utf8') as file:
            file.write(f'{mid},"{name}","Нет постера."')
        return
    else:
        img = Image.open(urlopen(url))
        img.thumbnail((100, 100))
        img.save(f'{PATH}m/{mid}.jpg')
