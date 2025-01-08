"""
Поиск страниц на Wikipedia и их обработка.
"""
import dateutil.parser as date_parser

import db
from decode_name import normal_name


def number_of_volumes(page: str) -> int:
    """
    Извлечение количества томов манги на Wikipedia.
    :param page: Страница манги на Wikipedia (HTML-код).
    :return: Количество томов манги.
    """
    pos = page.find('<th scope="row" class="infobox-label">Volumes</th><td class="infobox-data">') + 75
    if pos == 74:
        return 0
    return int(page[pos:page.find('</td>', pos)])


def date_of_premiere_manga(wp_page: str, title: str) -> str | bool:
    """
    Поиск даты премьеры (года выпуска) манги на Wikipedia.
    :param wp_page: Страница на Wikipedia (HTML-код).
    :param title: Наименование манги.
    :return: Дата премьеры манги в формате гггг-мм-чч или False, если дата на странице не найдена.
    """
    title = normal_name(title)
    pos = wp_page.find('<tbody><tr><td colspan="2" class="infobox-subheader" style="background:#CCF; font-size:125%; '
                       'font-style:italic; font-weight:bold;">') + 131
    pos2 = wp_page.find('</td></tr>', pos)
    if normal_name(wp_page[pos:pos2]) != title:
        while True:
            pos = wp_page.find('class="infobox-header"', pos) + 22
            pos = wp_page.find('<i>', pos) + 3
            pos2 = wp_page.find('</i>', pos)
            if normal_name(wp_page[pos:pos2]) == title:
                break
    posa = wp_page.find('<tr><th scope="row" class="infobox-label">Original run</th>'
                        '<td class="infobox-data"><span class="nowrap">', pos2) + 105
    posb = wp_page.find('<tr><th scope="row" class="infobox-label">Published</th>'
                        '<td class="infobox-data">', pos2) + 81
    if posa == 104 and posb != 80:
        pos1 = posb
        pos2 = wp_page.find('</td>', pos1)
    elif posb == 80 and posa != 104:
        pos1 = posa
        pos2 = wp_page.find('</span>', pos1)
    elif posa != 104 and posb != 80:
        pos1 = min(posa, posb)
        if pos1 == posa:
            pos2 = wp_page.find('</span>', pos1)
        else:
            pos2 = wp_page.find('</td>', pos1)
    else:
        return False
    date = wp_page[pos1:pos2]
    if len(date) == 4:
        return date_parser.parse(date).strftime('%Y') + '-12-31'
    return date_parser.parse(date).strftime('%Y-%m-%d')


def put_publication(publication: dict) -> int:
    """
    Добавление издания в БД из Wikipedia и возврат ID.
    :param publication: Издание.
    :return: ID издания в БД.
    """
    return db.put_publication(publication)


def publications_id(title: str, wp_page: str, oam: str) -> list[int] | bool:
    """
    Поиск ID соответствующих изданий из Wikipedia в БД.
    :param wp_page: Страница на Wikipedia (HTML-код).
    :param title: Наименование манги.
    :param oam: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID изданий в БД.
    """
    def posa_posb(tag: str) -> tuple[int, int]:
        posb = wp_page.find('</td>', posa, pos2)
        pos = wp_page.find('<a ', posa, posb)
        if pos != -1:
            posa_ = wp_page.find('>', pos, pos2) + 1
            posb = wp_page.find('</a>', posa_, pos2)
        else:
            if tag == 'td':
                posa_ = wp_page.find('>', posa, pos2) + 1
            else:
                posa_ = wp_page.find(f'<{tag}>', posa, pos2) + len(tag) + 2
            posb = wp_page.find(f'</{tag}>', posa_, pos2)
        return posa_, posb

    title = normal_name(title)
    cis = 'class="infobox-subheader"'
    cism = f'{cis} style="background:#CCF; font-weight:bold;">Manga</td></tr>'
    pos1 = wp_page.find(cism) + 25
    pose = wp_page.find('</tbody>', pos1)
    pos2 = 0
    while pos2 < pose:
        pos2 = wp_page.find(cis, pos1, pose)
        if pos2 == -1:
            pos2 = pose
        posa = wp_page.find('<tr><th colspan="2" class="infobox-header" style="background:#EEF; font-weight:normal;">'
                            '<i>', pos1, pos2) + 91
        if posa != 90:
            posb = wp_page.find('</i>', posa, pos2)
            if normal_name(wp_page[posa:posb]) == title:
                break
        pos1 = pos2 + 25
    else:
        return False
    posa = wp_page.find('class="infobox-label">Published&#160;by</th>', pos1, pos2) + 44
    posa, posb = posa_posb('td')
    publishing = wp_page[posa:posb]
    posa = wp_page.find('class="infobox-label">Magazine</th>', pos1, pos2) + 35
    if posa != 34:
        type_ = 1
        posa, posb = posa_posb('i')
    else:
        type_ = 2
        posa = wp_page.find('class="infobox-label">Imprint</th>', pos1, pos2)
        posa = wp_page.find('<td class="infobox-data">', posa, pos2) + 25
        posb = wp_page.find('</td>', posa, pos2)
    return db.publications_id(oam, [{'name': wp_page[posa:posb], 'exist': False, 'publishing': publishing,
                                     'type': type_}], put_publication)
