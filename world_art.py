"""
Поиск страниц на World Art и их обработка.
"""
import requests
from time import sleep
import re
from datetime import time

from decode_name import points_codes
from constants import *
from config import *
from decode_name import decode_name
import animenewsnetwork as ann
import db


# === Anime ===
def search_anime(search: str, form: str, year: int) -> str | None:
    """
    Поиск страницы anime на World Art.
    :param search: Искомое наименование.
    :param form: Формат.
    :param year: Год.
    :return: Страница (HTML-код), если найдена. Иначе — None.
    """
    search_ = points_codes(search)
    data = requests.get(WA + 'search.php', cookies=COOKIES_WA,
                        params={'public_search': search_, 'global_sector': A}).text
    aid = 0
    if data.find("<meta http-equiv='Refresh'") != -1:
        aid = int(data[data.find('?id=') + 4:-2])
    else:
        posa = 0
        ls = len(search_)
        wb = False
        str_sub = f'<a href = "{A}/{A}.php?id='
        lss = len(str_sub)
        while True:
            posa = data.find(str_sub, posa) + lss
            if posa == lss - 1:
                break
            pos = posa
            postd = data.find('</td>', pos)
            while True:
                pos = data.find(search_, pos, postd)
                if pos == -1:
                    break
                pos1 = pos + ls
                if (data[pos1:pos1 + 7] == '&nbsp;(' or data[pos1:pos1 + 4] == '<br>') and data[pos - 1:pos] == '>':
                    posf1 = data.find(', Япония, ', posa) + 10
                    posf2 = data.find(',', posf1)
                    if posf2 == -1:
                        posf2 = data.find(')', posf1)
                    if form in data[posf1:posf2] and str(year) in data[posf1 - 14:posf1 - 10]:
                        wb = True
                        break
                pos = pos1
            if wb:
                break
    if aid == 0 and posa in (33, 37):
        with open('report.csv', 'a', encoding='utf8') as file:
            file.write(
                f'"{search}","Ошибка. Возможно искомое наименование отредактировано и теперь не совпадает."\n'
            )
        return None
    elif aid == 0:
        aid = int(data[posa:data.find('" ', posa)])
    sleep(1)
    return requests.get(WAAA, {'id': aid}, cookies=COOKIES_WA).text


# === Manga ===
def search_manga_in_anime_page(page: str) -> str | None:
    """
    Поиск манги, связанной с anime на World Art.
    :param page: Страница anime на World Art (HTML-код, возвращённый search_anime).
    :return: Страница манги на World Art (HTML-код).
    """
    pos = page.find('<b>Снято по манге</b>')
    if pos == -1:
        return None
    pos = page.find(WAAM, pos) + 47
    mid = int(page[pos:page.find('" ', pos)])
    sleep(1)
    return requests.get(WAAM, {'id': mid}, cookies=COOKIES_WA).text


def manga_pages(page: str) -> list:
    """
    Поиск продолжений манги на World Art и формирования списка страниц.
    :param page: Страница манги на World Art (HTML-код, возвращённый search_manga_in_anime_page).
    :return: Список страниц.
    """
    pos1 = page.find("<link rel='canonical' href='") + 75
    mid = int(page[pos1:page.find("' />", pos1)])
    pos1 = page.find('<font size=2 color=#000000>Эта серия состоит из</font>', pos1)
    if pos1 == -1:
        return [page]
    i = 1
    res = []
    while True:
        pos1 = page.find(f'<td Valign=top> <b>#{i}&nbsp;</b></td>', pos1)
        if pos1 == -1:
            break
        if i == 1:
            pos2 = page.find('</table', pos1)
        pos1 = page.find(f'<a href = "{M}.php?id=', pos1, pos2) + 24
        nid = int(page[pos1:page.find('" ', pos1, pos2)])
        # if nid in (mid, ):
        #     i += 1
        #     continue
        if nid == mid:
            res.append(page)
        else:
            sleep(1)
            res.append(requests.get(WAAM, {'id': nid}, cookies=COOKIES_WA).text)
        i += 1
    if len(res):
        return res
    return [page]


def manga_in_ann(page: str, ann_pages: dict) -> tuple[str | bool, dict]:
    """
    Страница манги в ANN по ID из World Art.
    :param page: Страница манги на World Art (HTML-код).
    :param ann_pages: Словарь ANN-страниц манги ann_pages = {ann_id: обработана?}.
    :return: Кортеж: XML-страница манги на ANN, если есть ссылка, или False;
        и редактированный словарь ANN-страниц манги ann_pages.
    """
    pos1 = page.find('<b>Сайты</b>')
    pos2 = page.find('</table>', pos1)
    pos1 = page.find(f'{ANNE}{M}.php', pos1, pos2) + 58
    if pos1 == 57:
        return False, ann_pages
    mid = int(page[pos1:page.find("' ", pos1, pos2)])
    ann_pages[mid] = True  # Отметка об обработке страницы.
    return ann.xml({M: mid}), ann_pages


# def manga_in_wp(page: str) -> str | bool:
#     """
#     Страница манги в Wikipedia по ссылке из World Art.
#     :param page: Страница манги на World Art (HTML-код).
#     :return: Страница манги в Wikipedia, если найдена ссылка. Иначе — False.
#     """
#     pos1 = page.find('<b>Вики</b>')
#     pos2 = page.find('</table>', pos1)
#     pos = page.find('https://en.wikipedia.org/', pos1, pos2)
#     if pos == -1:
#         pos = page.find('http://en.wikipedia.org/', pos1, pos2)
#         if pos == -1:
#             return False
#     url = page[pos:page.find('" ', pos, pos2)]
#     sleep(1)
#     return requests.get(url).text


def put_people(pid: int, type_people: str) -> int:
    """
    Извлечение имён персоны из WA, добавление в БД и возврат ID.
    :param pid: ID персоны в WA.
    :param type_people: Тип персоны (специализация) из списка: ["AuthorOfManga", "Director"].
    :return: ID персоны в БД.
    """
    sleep(1)
    page = requests.get(f'{WA}people.php', {'id': pid}, cookies=COOKIES_WA).text
    pos1 = page.find('<font size=5>') + 13
    pos2 = page.find('</font>', pos1)
    data = {'narus': page[pos1:pos2]}
    pos1 = page.find('<b>Имя по-английски</b>', pos2)
    pos1 = page.find("class='review'>", pos1) + 15
    pos2 = page.find('</td>', pos1)
    data['narom'] = page[pos1:pos2]
    pos1 = page.find('<b>Оригинальное имя</b>', pos2)
    if pos1 != -1:
        pos1 = page.find("class='review'>", pos1) + 15
        pos2 = page.find('</td>', pos1)
        data['naori'] = decode_name(page[pos1:pos2])
    else:
        data['naori'] = data['narom']
    return db.put(type_people, data)


def authors_of_manga_id(page: str, oam: str) -> list:
    """
    Поиск ID соответствующих авторов манги из WA в БД.
    :param page: World Art страница (HTML-код).
    :param oam: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID авторов манги в БД.
    """
    pos1 = page.find('<b>Авторы</b>')
    pos2 = page.find('</table>', pos1)
    wa_authors = []
    i = 0
    while True:
        pos1 = page.find('/people.php?id=', pos1, pos2) + 15
        if pos1 == 14:
            break
        pos = page.find(" class='review'>", pos1, pos2) - 1
        wa_authors.append({'id': int(page[pos1:pos]), 'exist': False})
        pos1 = pos + 17
        wa_authors[i]['name'] = page[pos1:page.find('</a>', pos1, pos2)]
        i += 1
    pos1 = oam.find('<select name="maaum[]"')
    pos2 = oam.find('</select>', pos1)
    o_authors = re.findall(r'<option value="(.*?)">.*? / .*? / (.*?)</option>', oam[pos1:pos2])
    result = []
    for i in range(len(wa_authors)):
        for author in o_authors:
            if author[1] == wa_authors[i]['name']:
                result.append(int(author[0]))
                wa_authors[i]['exist'] = True
                break
    if len(result) < len(wa_authors):
        for wa_author in wa_authors:
            if not wa_author['exist']:
                result.append(put_people(wa_author['id'], 'AuthorOfManga'))
    return result


def put_publication(publication: dict) -> int:
    """
    Добавление издания в БД из World Art и возврат ID.
    :param publication: Издание.
    :return: ID издания в БД.
    """
    sleep(1)
    page = requests.get(f'{WA}company.php', {'id': publication['id']}, cookies=COOKIES_WA).text
    pos1 = page.find(f'<b>{publication['name']}</b>')
    pos2 = page.find('<b>Сериализация</b>', pos1)
    pos1 = page.find('company.php', pos1, pos2)
    pos1 = page.find("class='review'>", pos1, pos2) + 15
    publishing = page[pos1:page.find('</a>', pos1, pos2)]
    return db.put_publication({'name': publication['name'], 'type': 1, 'publishing': publishing})


def publications_id(page: str, oam: str) -> list[int]:
    """
    Поиск ID соответствующих изданий из WA в БД.
    :param page: World Art страница (HTML-код).
    :param oam: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID изданий в БД.
    """
    pos1 = page.find('<b>Сериализация</b>')
    pose = page.find('</table>', pos1)
    publications = []
    i = 0
    while True:
        pos1 = page.find('/company.php?id=', pos1, pose) + 16
        if pos1 == 15:
            break
        pos2 = page.find("' class='review'>", pos1, pose)
        publications.append({'id': int(page[pos1:pos2]), 'exist': False})
        pos1 = pos2 + 17
        publications[i]['name'] = page[pos1:page.find('</a>', pos1)]
        i += 1
    return db.publications_id(oam, publications, put_publication)


def genres_id(wa_page: str, o_page: str) -> list:
    """
    Поиск ID соответствующих жанров из WA в БД.
    :param wa_page: World Art страница (HTML-код).
    :param o_page: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID жанров в БД.
    """
    # wa_genres = re.findall(
    #     r"<a href='http://www\.world-art\.ru/animation/list\.php\?public_genre=\d+' class='review'>(.*?)</a>",
    #     wa_page
    # )
    pos_w1 = wa_page.find('<b>Жанр</b>')
    pos_w2 = wa_page.find('</table>', pos_w1)
    pos_w1 = wa_page.find("class='review'>", pos_w1, pos_w2) + 15
    result = []
    while pos_w1 > 14:
        genre = wa_page[pos_w1:wa_page.find('</a>', pos_w1, pos_w2)]
        if genre not in IGNORED_GENRES:
            pos_o2 = o_page.find(f'">{genre}</option>')
            pos_o1 = o_page.find('="', pos_o2 - 5) + 2
            result.append(int(o_page[pos_o1:pos_o2]))
        pos_w1 = wa_page.find("class='review'>", pos_w1, pos_w2) + 15
    return result


def name_rus(wa_page: str) -> str:
    """
    Извлечение наименования на русском из WA.
    :param wa_page: World Art страница (HTML-код).
    :return: Наименование на русском.
    """
    pos1 = wa_page.find('<font size=5>') + 13
    pos2 = wa_page.find('</font>', pos1)
    return decode_name(wa_page[pos1:pos2]).replace(' - ', ' — ').replace('...', '…')


def name_orig(wa_page: str, am: int | bool = 0) -> str:
    """
    Извлечение оригинального наименования из WA.
    :param wa_page: World Art страница (HTML-код).
    :param am: Переключатель: anime/манга (0/1).
    :return: Оригинальное наименование.
    """
    pos1 = wa_page.find(f'<b>Названи{'я' if am else 'е'} (кандзи)</b>')
    if pos1 == -1:
        pos1 = wa_page.find('<b>Названия (прочие)</b>')
        if pos1 == -1:
            pos1 = wa_page.find('<b>Названия (яп.)</b>')
    if pos1 != -1:
        pos1 = wa_page.find('Valign=top>', pos1) + 11
        pos2 = wa_page.find('</td>', pos1)
        return decode_name(wa_page[pos1:pos2])
    return name_rus(wa_page)


def name_rom(wa_page: str, am: int | bool = 0) -> str:
    """
    Извлечение наименования на ромадзи из WA.
    :param wa_page: World Art страница (HTML-код).
    :param am: Переключатель: anime/манга (0/1).
    :return: Наименование на ромадзи.
    """
    pos1 = wa_page.find(f'<b>Названи{'я (яп.' if am else 'е (ромадзи'})</b>')
    if pos1 == -1:
        pos1 = wa_page.find('<font size=5>') + 13
        pos2 = wa_page.find('</font>', pos1)
    else:
        pos1 = wa_page.find('Valign=top>', pos1) + 11
        pos2 = wa_page.find('</td>', pos1)
    return decode_name(wa_page[pos1:pos2]).replace(' - ', ' — ').replace('...', '…')


def name_eng(wa_page: str, am: int | bool = 0) -> str:
    """
    Извлечение наименования на английском из WA.
    :param wa_page: World Art страница (HTML-код).
    :param am: Переключатель: anime/манга (0/1).
    :return: Наименование на английском.
    """
    pos1 = wa_page.find(f'<b>Названи{'я' if am else 'е'} (англ.)</b>')
    if pos1 == -1:
        return ''
    pos1 = wa_page.find('Valign=top>', pos1) + 11
    pos2 = wa_page.find('</td>', pos1)
    return decode_name(wa_page[pos1:pos2]).replace(' - ', ' — ').replace('...', '…')


def manga_name_r(wa_name_r, *args) -> str:
    """
    Удаление в названии окончания « (манга)».
    :param wa_name_r: Функция name_rom или name_rus.
    :return: Исправленное название.
    """
    wa_name = wa_name_r(*args)
    pos = wa_name.find(' (манга)')
    if pos == -1:
        return wa_name
    return wa_name[:pos]


def id_manga_in_mu(page: str) -> int | bool:
    """
    Поиск ID манги в MangaUpdates по ссылке из World Art.
    :param page: Страница манги на World Art (HTML-код).
    :return: ID манги в MangaUpdates, если найдена ссылка. Иначе — False.
    """
    pos = page.find(WMU) + 43
    if pos == 42:
        return False
    pos2 = page.find("' ", pos)
    sleep(1)
    page = requests.get(WMU, {'id': page[pos:pos2]}).text
    pos = page.find('"identifier":') + 13
    pos2 = page.find(',', pos)
    return int(page[pos:pos2])


def date_of_premiere_manga(wa_page: str) -> str:
    """
    Поиск даты премьеры (года выпуска) манги на World Art.
    :param wa_page: Страница на World Art (HTML-код).
    :return: Дата премьеры манги в формате гггг-мм-чч.
    """
    pos1 = wa_page.find('<b>Год выпуска</b>')
    pose = wa_page.find('</table>', pos1)
    pos1 = wa_page.find('Valign=top>', pos1, pose) + 11
    return wa_page[pos1:wa_page.find('</td>', pos1, pose)] + '-12-31'


# === Anime ===
def anime_pages(page: str) -> list:
    """
    Поиск продолжений anime на World Art и формирования списка страниц.
    :param page: Страница anime на World Art (HTML-код, возвращённый search_anime).
    :return: Список страниц.
    """
    pos1 = page.find("<link rel='canonical' href='") + 79
    aid = int(page[pos1:page.find("' />", pos1)])
    pos1 = page.find('<font size=2>Информация о серии</font>', pos1)
    if pos1 == -1:
        return [page]
    i = 1
    res = []
    while True:
        pos1 = page.find(f'<td Valign=top width=20> <b>#{i}&nbsp;</b></td>', pos1)
        if pos1 == -1:
            break
        if i == 1:
            pos2 = page.find('</table', pos1)
        pos1 = page.find(f'<a href = "{WAAA}?id=', pos1, pos2) + 62
        nid = int(page[pos1:page.find('" ', pos1, pos2)])
        # if nid in (aid, ):
        #     i += 1
        #     continue
        if nid == aid:
            res.append(page)
        else:
            sleep(1)
            res.append(requests.get(WAAA, {'id': nid}, cookies=COOKIES_WA).text)
        i += 1
    if len(res):
        return res
    return [page]


def format_id(wa_page: str, o_page: str) -> int:
    """
    Поиск ID соответствующего формата из WA в БД.
    :param wa_page: World Art страница (HTML-код).
    :param o_page: Страница веб-приложения интерфейса БД (HTML-код).
    :return: ID формата в БД.
    """
    pos1 = wa_page.find('<b>Тип</b>') + 63
    pos2 = wa_page.find('</table>', pos1)
    pos = wa_page.find(' (', pos1, pos2)
    if pos == -1:
        pos = wa_page.find(',', pos1, pos2)
    result = wa_page[pos1:pos]
    pos2 = o_page.find(f'">{result}</option>')
    if pos2 == -1:
        return db.put('Format', {'name_f': result})
    pos1 = o_page.find('="', pos2 - 4) + 2
    return int(o_page[pos1:pos2])


def studios_id(wa_page: str, o_page: str) -> list:
    """
    Поиск ID соответствующих студий из WA в БД.
    :param wa_page: World Art страница (HTML-код).
    :param o_page: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID студий в БД.
    """
    url = f'{WAA}{A}_full_production.php'
    pos_w1 = wa_page.find('<b>Основное</b>') + 15
    pos_w1 = wa_page.find(url, pos_w1) + 67
    if pos_w1 == 66:
        return [1]
    pos_w2 = wa_page.find('" >компании', pos_w1)
    if pos_w2 == -1:
        return [1]
    aid = wa_page[pos_w1:pos_w2]
    sleep(1)
    data = requests.get(url, {'id': aid}, cookies=COOKIES_WA).text
    pos_w1 = data.find('<b>Производство:</b>')
    if pos_w1 == -1:
        return [1]
    pos_w2 = data.find('</table>', pos_w1)
    pos_w1 = data.find("class='estimation'>", pos_w1, pos_w2) + 19
    result = []
    while pos_w1 > 18:
        studio = decode_name(data[pos_w1:data.find('</a>', pos_w1, pos_w2)])
        pos_o2 = o_page.lower().find(f'">{studio.lower()}</option>')
        if pos_o2 != -1:
            pos_o1 = o_page.find('="', pos_o2 - 5) + 2
            result.append(int(o_page[pos_o1:pos_o2]))
        else:
            result.append(db.put('Studio', {'name_s': studio}))
        pos_w1 = data.find("class='estimation'>", pos_w1, pos_w2) + 19
    return result


def directors_id(wa_page: str, o_page: str) -> list:
    """
    Поиск ID соответствующих режиссёров из WA в БД.
    :param wa_page: World Art страница (HTML-код).
    :param o_page: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID режиссёров в БД.
    """
    url = f'{WAA}{A}_full_cast.php'
    pos1 = wa_page.find('<b>Основное</b>') + 15
    pos1 = wa_page.find(url, pos1) + 61
    if pos1 == 60:
        return [1]
    pos2 = wa_page.find('" >авторы', pos1)
    if pos2 == -1:
        return [1]
    aid = wa_page[pos1:pos2]
    sleep(1)
    data = requests.get(url, {'id': aid}, cookies=COOKIES_WA).text
    pos1 = data.find('<b>Режиссер:</b>')
    pos2 = data.find('</table>', pos1)
    ex = data.find('режиссер эпизода/сегмента')
    if ex == -1:
        ex = pos2
    wa_directors = []
    i = 0
    while True:
        pos1 = data.find('people.php?id=', pos1, pos2) + 14
        tr = data.find('<tr>', pos1, pos2)
        if tr == -1:
            tr = pos2
        if pos1 == 13 or tr > ex:
            break
        wa_directors.append({'id': int(data[pos1:data.find('" ', pos1, pos2)]), 'exist': False})
        pos1 = data.find("class='estimation'>", pos1, pos2) + 19
        wa_directors[i]['name'] = data[pos1:data.find('</a>', pos1, pos2)]
        i += 1
    pos1 = o_page.find('<select name="andir[]"')
    pos2 = o_page.find('</select>', pos1)
    o_directors = re.findall(r'<option value="(.*?)">.*? / .*? / (.*?)</option>', o_page[pos1:pos2])
    result = []
    for i in range(len(wa_directors)):
        for o_director in o_directors:
            if o_director[1] == wa_directors[i]['name']:
                result.append(int(o_director[0]))
                wa_directors[i]['exist'] = True
                break
    if len(result) < len(wa_directors):
        for wa_director in wa_directors:
            if not wa_director['exist']:
                result.append(put_people(wa_director['id'], 'Director'))
    return result


def anime_in_ann(wa_page: str) -> str | bool:
    """
    Страница anime в ANN по ID из World Art.
    :param wa_page: Страница anime на World Art (HTML-код).
    :return: XML-страница anime на ANN, если есть ссылка, или False.
    """
    pos1 = wa_page.find('<b>Сайты</b>')
    pos1 = wa_page.find('&nbsp;- <noindex>', pos1)
    pos2 = wa_page.find('<table ', pos1)
    pos1 = wa_page.find(f'{SANNE}anime.php', pos1, pos2) + 59
    if pos1 == 57:
        return False
    aid = int(wa_page[pos1:wa_page.find("' ", pos1, pos2)])
    return ann.xml({'anime': aid})


def number_of_episodes(wa_page: str) -> int:
    """
    Извлечение количества эпизодов из WA.
    :param wa_page: World Art страница (HTML-код).
    :return: Количество эпизодов.
    """
    pos1 = wa_page.find('<b>Тип</b>')
    pos2 = wa_page.find('</table>', pos1)
    pos1 = wa_page.find(' (', pos1, pos2) + 2
    if pos1 == 1:
        return 1
    pos2 = wa_page.find(' эп.', pos1, pos2)
    return int(wa_page[pos1:pos2])


def duration(wa_page: str):
    """
    Извлечение продолжительности эпизода из WA.
    :param wa_page: World Art страница (HTML-код).
    :return: Продолжительность эпизода в формате чч:мм.
    """
    pos1 = wa_page.find('<b>Тип</b>')
    pos2 = wa_page.find('</table>', pos1)
    pos = wa_page.find('), ', pos1, pos2) + 3
    if pos == 2:
        pos = wa_page.find(', ', pos1, pos2) + 2
    pos2 = wa_page.find(' мин.', pos1, pos2)
    m = int(wa_page[pos:pos2])
    h = 0
    if m > 60:
        h = m // 60
        m = m - 60 * h
    t = time(h, m)
    return t.isoformat('minutes')


def date_of_premiere_anime(wa_page: str) -> str:
    """
    Извлечение даты премьеры из WA.
    :param wa_page: World Art страница (HTML-код).
    :return: Дата премьеры в формате гггг-мм-дд.
    """
    pos = wa_page.find('<b>Выпуск</b>')
    if pos == -1:
        pos = wa_page.find('<b>Премьера</b>')
    res = ''
    for i in range(3):
        pos = wa_page.find("class='review'>", pos) + 15
        res = wa_page[pos:pos + (2 if i < 2 else 4)] + ('-' + res if i > 0 else '')
    return res


def notes(wa_page: str) -> str:
    """
    Извлечение примечаний из WA.
    :param wa_page: World Art страница (HTML-код).
    :return: Примечания.
    """
    pos1 = wa_page.find('<b>Тип</b>')
    pos2 = wa_page.find('</table>', pos1)
    pos1 = wa_page.find(' (', pos1, pos2) + 2
    if pos1 == 1:
        return ''
    pos1 = wa_page.find(' + ', pos1, pos2) + 1
    if pos1 == 0:
        return ''
    pos2 = wa_page.find('), ', pos1, pos2)
    return wa_page[pos1:pos2]


# === Manga ===
def search_publication_or_publishing(name: str) -> str | None:
    """
    Поиск страницы издания или издательства по наименованию в WA.
    :param name: Наименование издания или издательства.
    :return: Искомая страница (HTML-код) или None.
    """
    search = points_codes(name)
    sleep(1)
    data = requests.get(WA + 'search.php', cookies=COOKIES_WA,
                        params={'public_search': search, 'global_sector': 'company'}).text
    pid = 0
    if data.find("<meta http-equiv='Refresh'") != -1:
        pid = int(data[data.find('?id=') + 4:-2])
    else:
        posa = 0
        ls = len(search)
        wb = False
        str_sub = f'<a href = "company.php?id='
        lss = len(str_sub)
        while True:
            posa = data.find(str_sub, posa) + lss
            if posa == lss - 1:
                break
            pos = posa
            postd = data.find('</td>', pos)
            while True:
                pos = data.find(search, pos, postd)
                if pos == -1:
                    break
                pos1 = pos + ls
                if data[pos1:pos1 + 4] == '</a>' and data[pos - 1:pos] == '>':
                    wb = True
                    break
                pos = pos1
            if wb:
                break
    if pid == 0:
        try:
            pid = int(data[posa:data.find('" ', posa)])
        except ValueError:
            return None
    sleep(1)
    return requests.get(f'{WA}company.php', {'id': pid}, cookies=COOKIES_WA).text


def extraction_publishing(page: str) -> str:
    """
    Извлечение издательства из страницы издания на WA.
    :param page: Страница издания на WA (HTML-код).
    :return: Наименование издательства.
    """
    pos1 = page.find('<b>Издатель</b>') + 15
    pose = page.find('</table>', pos1)
    pos1 = page.find('<a href=', pos1, pose)
    pos1 = page.find('>', pos1, pose)
    return page[pos1:page.find('</a>', pos1, pose)]


def valid_publication(publishing: str, publication: str) -> bool:
    """
    Проверка принадлежности издания издательству по БД World Art.
    :param publishing: Издательство.
    :param publication: Издание.
    :return: Найдено или нет.
    """
    page = search_publication_or_publishing(publishing)
    pos1 = page.find('<b>Принадлежащие издания</b>') + 28
    pose = page.find('</table>', pos1)
    while True:
        pos1 = page.find("<a href='company.php?id=", pos1, pose) + 24
        if pos1 == 23:
            return False
        pos2 = page.find("'", pos1, pose)
        posa = page.find('>', pos2, pose) + 1
        posb = page.find('</a>', posa, pose)
        if page[posa:posb] == publication:
            return True
        pos1 = posb
