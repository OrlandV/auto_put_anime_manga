"""
Поиск страниц на Wikipedia и их обработка.
"""
import dateutil.parser as date_parser

from decode_name import normal_name, month
import db


def search_manga(title_rom: str, title_eng: str, wp_page: str) -> tuple[int, int] | bool:
    """
    Поиск манги в инфобоксе страницы в Wikipedia.
    :param wp_page: Страница на Wikipedia (HTML-код).
    :param title_rom: Ромадзи наименование манги.
    :param title_eng: Английское наименование манги.
    :return: Кортеж позиций в HTML-коде.
    """
    cis = 'class="infobox-subheader"'
    subheader = f'<tr><td colspan="2" {cis} style="background:#CCF; font-weight:bold;">'
    header = '<tr><th colspan="2" class="infobox-header" style="background:#EEF; font-weight:normal;"><i>'
    title_rom = normal_name(title_rom)
    title_eng = normal_name(title_eng)
    pos = wp_page.find('<p><i><b>') + 9
    pose = wp_page.find('. ', pos)
    nen = normal_name(wp_page[pos:wp_page.find('</b></i>', pos, pose)])
    pos1 = wp_page.find(subheader) + 89
    pose = wp_page.find('</tbody>', pos1)
    pos2 = 0
    while pos2 < pose:
        pos2 = wp_page.find(subheader, pos1, pose)
        if pos2 == -1:
            pos2 = pose
        if wp_page[pos1:pos1 + 5] == 'Manga':
            if nen == title_eng:
                return pos1, pos2
            posa = wp_page.find(header, pos1, pos2) + 91
            if posa != 90:
                posb = wp_page.find('</i>', posa, pos2)
                if normal_name(wp_page[posa:posb]) == title_rom:
                    return pos1, pos2
        pos1 = pos2 + 89
    return False


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


def date_of_premiere_manga(wp_page: str, title_rom: str, title_eng: str) -> str | bool:
    """
    Поиск даты премьеры (года выпуска) манги на Wikipedia.
    :param wp_page: Страница на Wikipedia (HTML-код).
    :param title_rom: Ромадзи наименование манги.
    :param title_eng: Английское наименование манги.
    :return: Дата премьеры манги в формате гггг-мм-чч или False, если дата на странице не найдена.
    """
    if pp := search_manga(title_rom, title_eng, wp_page):
        pos1, pos2 = pp
    else:
        return False
    posa = wp_page.find('<tr><th scope="row" class="infobox-label">Original run</th>'
                        '<td class="infobox-data"><span class="nowrap">', pos1, pos2) + 105
    posb = wp_page.find('<tr><th scope="row" class="infobox-label">Published</th>'
                        '<td class="infobox-data">', pos1, pos2) + 81
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
    date_ = date.split(' ')
    if len(date_) == 2:
        return month(date)
    return date_parser.parse(date).strftime('%Y-%m-%d')


def put_publication(publication: dict) -> int:
    """
    Добавление издания в БД из Wikipedia и возврат ID.
    :param publication: Издание.
    :return: ID издания в БД.
    """
    return db.put_publication(publication)


def publications_id(title_rom: str, title_eng: str, wp_page: str, oam: str) -> list[int] | bool:
    """
    Поиск ID соответствующих изданий из Wikipedia в БД.
    :param wp_page: Страница на Wikipedia (HTML-код).
    :param title_rom: Ромадзи наименование манги.
    :param title_eng: Английское наименование манги.
    :param oam: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID изданий в БД.
    """
    def posa_posb(tag: str) -> list[tuple[int, int]]:
        """
        «Координаты» наименования изданий или издательств в HTML-коде.
        :param tag: Тэг td или i.
        :return: Список кортежей «координат».
        """
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
        posu = wp_page.find('<ul>', posa_, posb)
        if posu != -1:
            res = []
            posu2 = wp_page.find('</ul>', posu, posb)
            posl1 = posu
            i = 0
            while posl1 < posu2:
                i += 1
                posl1 = wp_page.find('<li>', posl1, posb) + 4
                posl2 = wp_page.find('</li>', posl1, posb)
                if i % 2 != 0:
                    res.append((posl1, posl2))
                posl1 = posl2 + 5
            return res
        return [(posa_, posb)]

    if pp := search_manga(title_rom, title_eng, wp_page):
        pos1, pos2 = pp
    else:
        return False
    posa = wp_page.find('class="infobox-label">Published&#160;by</th>', pos1, pos2) + 44
    posa, posb = posa_posb('td')[0]
    publishing = wp_page[posa:posb]
    posa = wp_page.find('class="infobox-label">Magazine</th>', pos1, pos2) + 35
    publications = []
    if posa != 34:
        for pp in posa_posb('i'):
            posa, posb = pp
            publications.append({'name': wp_page[posa:posb], 'publishing': publishing, 'type': 1, 'exist': False})
    else:
        posa = wp_page.find('class="infobox-label">Imprint</th>', pos1, pos2)
        posa = wp_page.find('<td class="infobox-data">', posa, pos2) + 25
        posb = wp_page.find('</td>', posa, pos2)
        publications.append({'name': wp_page[posa:posb], 'publishing': publishing, 'type': 2, 'exist': False})
    return db.publications_id(oam, publications, put_publication)
