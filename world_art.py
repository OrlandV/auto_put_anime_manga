"""
Поиск страниц в World Art (далее — WA) и их обработка.
"""
import requests
from time import sleep

from decode_name import points_codes, decode_name, hours_minutes
from constants import *
from config import COOKIES_WA, IGNORED_GENRES


def html(id_: int, am: bool = False, url: str | None = None) -> str:
    """
    Получение HTML-кода страницы в WA.
    :param id_: ID в URI-параметрах.
    :param am: Переключатель: anime/манга (0/1 | False/True).
    :param url: URL раздела WA.
    :return: HTML-код страницы в WA.
    """
    if not url:
        url = WAAM if am else WAAA
    sleep(1)
    return requests.get(url, {'id': id_}, cookies=COOKIES_WA).text


def anime_pages(aid: int) -> dict[int, str]:
    """
    Поиск продолжений anime в WA и формирование словаря страниц.
    :param aid: ID anime в WA.
    :return: Словарь страниц в WA.
    """
    page = html(aid)
    pos1 = page.find('<font size=2>Информация о серии</font>')
    if pos1 == -1:
        return {aid: page}
    i = 1
    res = {}
    while True:
        pos1 = page.find(f'<td Valign=top width=20> <b>#{i}&nbsp;</b></td>', pos1)
        if pos1 == -1:
            break
        if i == 1:
            pos2 = page.find('</table', pos1)
        pos1 = page.find(f'<a href = "{WAAA}?id=', pos1, pos2) + 62
        nid = int(page[pos1:page.find('" ', pos1, pos2)])
        res[nid] = page if nid == aid else html(nid)
        i += 1
    if len(res):
        return res
    return {aid: page}


def report(search: str, am: bool = False) -> None:
    """
    Запись в report.csv строки с искомым наименованием.
    :param search: Искомое наименование.
    :param am: Переключатель: anime/манга (0/1 | False/True).
    """
    with open('report.csv', 'a', encoding='utf8') as file:
        file.write(
            f'{M if am else A},"{search}",'
            '"Ошибка. Возможно искомое наименование отредактировано и теперь не совпадает."\n'
        )


def search_anime(search: str, year: int, form: str) -> dict[int, str] | None:
    """
    Поиск anime в WA.
    :param search: Наименование anime.
    :param year: Год премьеры.
    :param form: Формат.
    :return: Словарь страниц anime в WA либо None.
    """
    search_ = points_codes(search)
    data = requests.get(WA + 'search.php', cookies=COOKIES_WA,
                        params={'public_search': search_, 'global_sector': AN}).text
    aid = 0
    if data.find("<meta http-equiv='Refresh'") != -1:
        aid = int(data[data.find('?id=') + 4:-2])
    else:
        posa = 0
        ls = len(search_)
        wb = False
        str_sub = f'<a href = "{AN}/{AN}.php?id='
        lss = len(str_sub)
        if form:
            while not wb:
                posa = data.find(str_sub, posa) + lss
                if posa == lss - 1:
                    report(search)
                    return
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
        else:
            animes = []
            while True:
                posa = data.find(str_sub, posa) + lss
                if posa == lss - 1:
                    break
                aid = int(data[posa:data.find('" ', posa)])
                postd = data.find('</td>', posa)
                posa = data.find("class='review'>", posa, postd) + 15
                names = data[posa:postd].replace('</a>', '').replace('<br>', '\n')
                animes.append((aid, names))
                posa = postd
            animes = animes[::-1]
            text = '\n0. *** Подходящего варианта нет ***'
            for i, anime in enumerate(animes):
                text += f'\n{i + 1}. {anime[1]}'
            print(f'Укажите номер anime, подходящего под искомое наименование «{search}»:{text}')
            while True:
                num = input('Укажите номер: ')
                if num.isdigit():
                    break
                print('Ошибка! Требуется ввести целое число.')
            num = int(num)
            if not num:
                return
            aid = animes[num - 1][0]
    if not aid:
        aid = int(data[posa:data.find('" ', posa)])
    return anime_pages(aid)


def manga_pages(mid: int) -> dict[int, str]:
    """
    Поиск продолжений манги в WA и формирование словаря страниц.
    :param mid: Страница манги в WA (HTML-код, возвращённый search_manga_in_anime_page).
    :return: Словарь страниц манги в WA.
    """
    page = html(mid, True)
    pos1 = page.find('<font size=2 color=#000000>Эта серия состоит из</font>')
    if pos1 == -1:
        return {mid: page}
    i = 1
    res = {}
    while True:
        pos1 = page.find(f'<td Valign=top> <b>#{i}&nbsp;</b></td>', pos1)
        if pos1 == -1:
            break
        if i == 1:
            pos2 = page.find('</table', pos1)
        pos1 = page.find(f'<a href = "{M}.php?id=', pos1, pos2) + 24
        nid = int(page[pos1:page.find('" ', pos1, pos2)])
        res[nid] = page if nid == mid else html(nid, True)
        i += 1
    if len(res):
        return res
    return {mid: page}


def search_manga(search: str, year: int) -> dict[int, str] | None:
    """
    Поиск манги в WA.
    :param search: Наименование манги.
    :param year: Год премьеры.
    :return: Словарь страниц манги в WA.
    """
    search_ = points_codes(search)
    data = requests.get(WA + 'search.php', cookies=COOKIES_WA,
                        params={'public_search': search_, 'global_sector': M}).text
    mid = 0
    if data.find("<meta http-equiv='Refresh'") != -1:
        mid = int(data[data.find('?id=') + 4:-2])
    else:
        posa = 0
        ls = len(search_)
        wb = False
        str_sub = f'<a href = "{AN}/{M}.php?id='
        lss = len(str_sub)
        while not wb:
            posa = data.find(str_sub, posa) + lss
            if posa == lss - 1:
                report(search, True)
                return
            pos = posa
            postd = data.find('</td>', pos)
            while True:
                pos = data.find(search_, pos, postd)
                if pos == -1:
                    break
                pos1 = pos + ls
                if (data[pos1:pos1 + 7] == '&nbsp;(' or data[pos1:pos1 + 4] == '<br>') and data[pos - 1:pos] == '>':
                    pos1 = data.find('</a>', posa) - 5
                    if str(year) in data[pos1:pos1 + 4]:
                        wb = True
                        break
                pos = pos1
    if not mid:
        mid = int(data[posa:data.find('" ', posa)])
    return manga_pages(mid)


def manga_pages_from_anime(wa_manga_pages: dict[int, str] | None, wa_anime_pages: dict[int, str] | None
                           ) -> tuple[dict[int, str], dict[int, int]]:
    """
    Поиск связанной с anime манги и добавление её в словарь страниц манги в WA.
    А также составление словаря связей anime с мангой.
    :param wa_manga_pages: Словарь страниц манги в WA.
    :param wa_anime_pages: Словарь страниц anime в WA.
    :return: Кортеж: обновлённый словарь страниц манги в WA и словарь связей anime с мангой.
    """
    def related_manga(mid: int) -> None:
        """
        Добавление манги в словарь страниц манги в WA.
        :param mid: ID манги в WA.
        """
        nonlocal wa_manga_pages
        manga = html(mid, True)
        if not wa_manga_pages:
            wa_manga_pages = {}
        wa_manga_pages[mid] = manga
        pos = manga.find('<font size=2 color=#000000>Эта серия состоит из</font>')
        if pos == -1:
            return
        i = 1
        while True:
            pos = manga.find(f'<td Valign=top> <b>#{i}&nbsp;</b></td>', pos)
            if pos == -1:
                break
            if i == 1:
                pos2 = manga.find('</table', pos)
            pos = manga.find(f'<a href = "{M}.php?id=', pos, pos2) + 24
            nid = int(manga[pos:manga.find('" ', pos, pos2)])
            if nid not in wa_manga_pages:
                related_manga(nid)
            i += 1

    rm = {}
    for aid, anime in wa_anime_pages.items():
        pos = anime.find('<b>Снято по манге</b>')
        if pos == -1:
            continue
        pos = anime.find(WAAM, pos) + 47
        mid = int(anime[pos:anime.find('" ', pos)])
        if not wa_manga_pages or mid not in wa_manga_pages:
            related_manga(mid)
        rm[aid] = mid
    return wa_manga_pages, rm


def related_anime(wa_anime_pages: dict[int, str], aid: int) -> dict[int, str]:
    """
    Поиск связанного anime в WA и добавление его в словарь страниц anime в WA.
    :param wa_anime_pages: Словарь страниц anime в WA.
    :param aid: ID anime в WA.
    :return: Обновлённый словарь страниц anime в WA.
    """
    anime = html(aid)
    wa_anime_pages[aid] = anime
    pos = anime.find('<font size=2>Информация о серии</font>')
    if pos == -1:
        return wa_anime_pages
    i = 1
    while True:
        pos = anime.find(f'<td Valign=top width=20> <b>#{i}&nbsp;</b></td>', pos)
        if pos == -1:
            break
        if i == 1:
            pos2 = anime.find('</table', pos)
        pos = anime.find(f'<a href = "{WAAA}?id=', pos, pos2) + 62
        nid = int(anime[pos:anime.find('" ', pos, pos2)])
        if nid not in wa_anime_pages:
            wa_anime_pages = related_anime(wa_anime_pages, nid)
        i += 1


def anime_id_from_manga(page: str) -> list[int | None]:
    """
    Извлечение ID anime в WA из страницы манги в WA и формирование списка.
    :param page: Страница манги (HTML-код) в WA.
    :return: Список ID anime в WA.
    """
    pos = page.find('<b><font size=2 color=#000000>По этой манге снято аниме</font></b>')
    if pos == -1:
        return []
    ids = []
    pos = page.find(AN + '.php', pos) + 17
    while pos > 16:
        ids.append(int(page[pos:page.find('" ', pos)]))
        pos = page.find(AN + '.php', pos) + 17
    return ids


def anime_pages_from_manga(wa_anime_pages: dict[int, str], wa_manga_pages: dict[int, str]) -> dict[int, str]:
    """
    Добавление anime, связанных с мангой из словаря страниц манги в WA, в словарь страниц anime в WA.
    :param wa_anime_pages: Словарь страниц anime в WA.
    :param wa_manga_pages: Словарь страниц манги в WA.
    :return: Обновлённый словарь страниц anime в WA.
    """
    for manga in wa_manga_pages.values():
        aids = anime_id_from_manga(manga)
        if len(aids):
            for aid in aids:
                if aid not in wa_anime_pages:
                    wa_anime_pages = related_anime(wa_anime_pages, aid)
    return wa_anime_pages


def ann_anime_id(wa_page: str) -> int | None:
    """
    Извлечение ID anime в ANN по ссылке в WA.
    :param wa_page: Страница anime (HTML-код) в WA.
    :return: ID anime в ANN, если найдена ссылка в WA. Иначе — None.
    """
    pos1 = wa_page.find('<b>Сайты</b>')
    pos1 = wa_page.find('&nbsp;- <noindex>', pos1)
    pos2 = wa_page.find('<table ', pos1)
    pos1 = wa_page.find(f'{SANNE}{A}.php', pos1, pos2) + 59
    if pos1 == 58:
        return
    return int(wa_page[pos1:wa_page.find("' ", pos1, pos2)])


def ann_manga_id(wa_page: str) -> int | None:
    """
    Извлечение ID манги в ANN по ссылке в WA.
    :param wa_page: Страница манги (HTML-код) в WA.
    :return: ID манги в ANN, если найдена ссылка в WA. Иначе — None.
    """
    pos1 = wa_page.find('<b>Сайты</b>')
    pos2 = wa_page.find('</table>', pos1)
    pos1 = wa_page.find(f'{ANNE}{M}.php', pos1, pos2) + 58
    if pos1 == 57:
        return
    return int(wa_page[pos1:wa_page.find("' ", pos1, pos2)])


def wp_title(wa_page: str) -> str | None:
    """
    Извлечение заголовка в WP по ссылке в WA.
    :param wa_page: Страница (HTML-код) в WA.
    :return: Заголовок в WP, если найдена ссылка в WA. Иначе — None.
    """
    from urllib.parse import unquote

    pos1 = wa_page.find('<b>Википедия</b>')
    pos1 = wa_page.find('&nbsp;- <noindex>', pos1)
    pos2 = wa_page.find('<table ', pos1)
    pos1 = wa_page.find(WPE, pos1, pos2) + 29
    if pos1 == 28:
        return
    return unquote(wa_page[pos1:wa_page.find("' ", pos1, pos2)])


def mu_manga_id(wa_page: str) -> int | None:
    """
    Поиск ID манги в MU по ссылке в WA.
    :param wa_page: Страница манги (HTML-код) в WA.
    :return: ID манги в MU, если найдена ссылка в WA. Иначе — None.
    """
    pos = wa_page.find(WMU) + 43
    if pos == 42:
        return
    pos2 = wa_page.find("' ", pos)
    sleep(1)
    page = requests.get(WMU, {'id': wa_page[pos:pos2]}).text
    pos = page.find('"identifier":') + 13
    pos2 = page.find(',', pos)
    return int(page[pos:pos2])


def title_rom(page: str, am: bool = False) -> str:
    """
    Извлечение ромадзи наименования из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :param am: Переключатель: anime/манга (False/True).
    :return: Ромадзи наименование в WA.
    """
    pos1 = page.find(f'<b>Названи{'я (яп.' if am else 'е (ромадзи'})</b>')
    if pos1 == -1:
        pos1 = page.find('<font size=5>') + 13
        pos2 = page.find('</font>', pos1)
    else:
        pos1 = page.find('Valign=top>', pos1) + 11
        pos2 = page.find('</td>', pos1)
    return decode_name(page[pos1:pos2]).replace(' - ', ' — ').replace('...', '…')


def manga_date_of_premiere(page: str, full_format: bool = True) -> str:
    """
    Извлечение даты премьеры манги из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :param full_format: Флаг полного формата даты (гггг.мм.дд). Если False, то только год (гггг).
    :return: Дата премьеры манги в WA.
    """
    pos1 = page.find('<b>Год выпуска</b>')
    pose = page.find('</table>', pos1)
    pos1 = page.find('Valign=top>', pos1, pose) + 11
    return page[pos1:page.find('</td>', pos1, pose)] + ('-12-31' if full_format else '')


def title_rus(page: str) -> str:
    """
    Извлечение русского наименования из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Русское наименование в WA.
    """
    pos1 = page.find('<font size=5>') + 13
    pos2 = page.find('</font>', pos1)
    return decode_name(page[pos1:pos2]).replace(' - ', ' — ').replace('...', '…')


def title_orig(page: str, am: bool = False) -> str:
    """
    Извлечение оригинального наименования из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :param am: Переключатель: anime/манга (False/True).
    :return: Оригинальное наименование в WA.
    """
    pos1 = page.find(f'<b>Названи{'я' if am else 'е'} (кандзи)</b>')
    if pos1 == -1:
        pos1 = page.find('<b>Названия (прочие)</b>')
        if pos1 == -1:
            pos1 = page.find('<b>Названия (яп.)</b>')
    if pos1 != -1:
        pos1 = page.find('Valign=top>', pos1) + 11
        pos2 = page.find('</td>', pos1)
        return decode_name(page[pos1:pos2])
    return title_rus(page)


def manga_title_r(func, *args) -> str:
    """
    Удаление в наименовании окончания « (манга)».
    :param func: Функция title_rom или title_rus.
    :param args: аргументы функций title_rom или title_rus.
    :return: Исправленное наименование.
    """
    manga_title = func(*args)
    return manga_title.removesuffix(' (манга)')


def title_eng(page: str, am: bool = False) -> str:
    """
    Извлечение английского наименования из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :param am: Переключатель: anime/манга (False/True).
    :return: Английское наименование в WA.
    """
    pos1 = page.find(f'<b>Названи{'я' if am else 'е'} (англ.)</b>')
    if pos1 == -1:
        return ''
    pos1 = page.find('Valign=top>', pos1) + 11
    pos2 = page.find('</td>', pos1)
    return decode_name(page[pos1:pos2]).replace(' - ', ' — ').replace('...', '…')


def people(pid: int) -> dict[str, str]:
    """
    Извлечение имён персоны из страницы в WA.
    :param pid: ID персоны в WA.
    :return: Словарь имён персоны в WA.
    """
    page = html(pid, url=f'{WA}people.php')
    pos1 = page.find('<font size=5>') + 13
    pos2 = page.find('</font>', pos1)
    data = {'name_rus': page[pos1:pos2]}
    pos1 = page.find('<b>Имя по-английски</b>', pos2)
    pos1 = page.find("class='review'>", pos1) + 15
    pos2 = page.find('</td>', pos1)
    data['name_rom'] = page[pos1:pos2]
    pos1 = page.find('<b>Оригинальное имя</b>', pos2)
    if pos1 != -1:
        pos1 = page.find("class='review'>", pos1) + 15
        pos2 = page.find('</td>', pos1)
        data['name_orig'] = decode_name(page[pos1:pos2])
    else:
        data['name_orig'] = data['name_rom']
    return data


def authors(page: str) -> dict[int, dict[str, str]]:
    """
    Извлечение имён авторов из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Словарь авторов — словарей имён авторов (персон) в WA.
    """
    pos1 = page.find('<b>Авторы</b>')
    pos2 = page.find('</table>', pos1)
    result = {}
    while True:
        pos1 = page.find('/people.php?id=', pos1, pos2) + 15
        if pos1 == 14:
            break
        pos = page.find(" class='review'>", pos1, pos2) - 1
        id_ = int(page[pos1:pos])
        result[id_] = people(id_)
    return result


def publications(page: str) -> dict[int, dict[str, str]]:
    """
    Извлечение изданий из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Словарь изданий в WA.
    """
    pos1 = page.find('<b>Сериализация</b>')
    pose = page.find('</table>', pos1)
    result = {}
    while True:
        pos1 = page.find('/company.php?id=', pos1, pose) + 16
        if pos1 == 15:
            break
        pos2 = page.find("'", pos1, pose)
        id_ = int(page[pos1:pos2])
        pos1 = pos2 + 17
        publication = page[pos1:page.find('</a>', pos1)]
        page_ = html(id_, url=f'{WA}company.php')
        posa = page_.find(f'<b>{publication}</b>')
        posb = page_.find('<b>Сериализация</b>', posa)
        posa = page_.find('company.php', posa, posb)
        posa = page_.find("class='review'>", posa, posb) + 15
        publishing = page_[posa:page_.find('</a>', posa, posb)]
        if publication == "Morning":
            publication = "Shuukan Morning"
        result[id_] = {'publication': publication, 'publishing': publishing}
    return result


def genres(page: str) -> list[str]:
    """
    Извлечение жанров из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Список жанров в WA.
    """
    pos_w1 = page.find('<b>Жанр</b>')
    pos_w2 = page.find('</table>', pos_w1)
    pos_w1 = page.find("class='review'>", pos_w1, pos_w2) + 15
    result = []
    while pos_w1 > 14:
        genre = page[pos_w1:page.find('</a>', pos_w1, pos_w2)]
        if genre not in IGNORED_GENRES:
            result.append(genre)
        pos_w1 = page.find("class='review'>", pos_w1, pos_w2) + 15
    return result


def poster(page: str, am: bool = False) -> str | None:
    """
    Извлечение URL постера из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :param am: Переключатель: anime/манга (False/True).
    :return: URL постера в WA.
    """
    pos = page.find("<a href='img/") if am else page.find(f"<a href='{WAA}{AN}_poster.php?id=")
    if pos != -1:
        if am:
            return f'{WAA}img/' + page[pos + 13:page.find("' ", pos)]
        else:
            pos = page.find(f"<img src='{WAA}img/", pos)
            return page[pos + 10:page.find("' ", pos)]


def extraction_manga(page: str) -> dict[str, str | dict[int, dict[str, str]] | dict[int, str] | list[str]]:
    """
    Извлечение манги из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Словарь данных по манги в WA.
    {
        'name_orig': str,
        'name_rom': str,
        'name_eng': str,
        'name_rus': str,
        'author_of_manga': dict[int, dict[str, str]],
        'date_of_premiere': str,
        'publication': dict[int, dict[str, str]],
        'genre': list[str],
        'poster': str
    }
    """
    result = {
        'name_orig': title_orig(page, True),
        'name_rom': manga_title_r(title_rom, page, True),
        'name_eng': title_eng(page, True),
        'name_rus': manga_title_r(title_rus, page),
        'author_of_manga': authors(page),
        'date_of_premiere': manga_date_of_premiere(page),
        'publication': publications(page),
        'genre': genres(page),
        'poster': poster(page, True),
        'ann': ann_manga_id(page)
    }
    if result['name_rus'] == result['name_rom']:
        result['name_rus'] = ''
    if result['name_eng'] == '' and result['name_orig'] == result['name_rom']:
        result['name_eng'] = result['name_rom']
    elif result['name_rus'] == '' and result['name_eng'] and result['name_rom']:
        result['name_rus'] = result['name_rom']
        result['name_rom'] = result['name_eng']
    return result


def anime_format(page: str) -> str:
    """
    Извлечение формата anime из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Формат anime в WA.
    """
    pos1 = page.find('<b>Тип</b>') + 63
    pos2 = page.find('</table>', pos1)
    pos = page.find(' (', pos1, pos2)
    if pos == -1:
        pos = page.find(',', pos1, pos2)
    return page[pos1:pos]


def number_of_episodes(page: str) -> int:
    """
    Извлечение количества эпизодов из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Количество эпизодов в WA.
    """
    pos1 = page.find('<b>Тип</b>')
    pos2 = page.find('</table>', pos1)
    pos1 = page.find(' (', pos1, pos2) + 2
    if pos1 == 1:
        return 1
    pos2 = page.find(' эп.', pos1, pos2)
    return int(page[pos1:pos2])


def duration(page: str) -> str:
    """
    Извлечение продолжительности эпизода из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Продолжительность эпизода в формате чч:мм в WA.
    """
    pos1 = page.find('<b>Тип</b>')
    pos2 = page.find('</table>', pos1)
    pos = page.find('), ', pos1, pos2) + 3
    if pos == 2:
        pos = page.find(', ', pos1, pos2) + 2
    pos2 = page.find(' мин.', pos1, pos2)
    return hours_minutes(int(page[pos:pos2]))


def anime_date_of_premiere(page: str) -> str:
    """
    Извлечение даты премьеры anime из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Дата премьеры anime в WA.
    """
    pos = page.find('<b>Выпуск</b>')
    if pos == -1:
        pos = page.find('<b>Премьера</b>')
    res = ''
    for i in range(3):
        pos = page.find("class='review'>", pos) + 15
        res = page[pos:pos + (2 if i < 2 else 4)] + ('-' + res if i > 0 else '')
    return res


def studios(page: str) -> list[str] | None:
    """
    Извлечение студий из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Список наименований студий в WA. None — если нет информации о студиях.
    """
    url = f'{WAA}{AN}_full_production.php'
    pos_w1 = page.find('<b>Основное</b>') + 15
    pos_w1 = page.find(url, pos_w1) + 67
    if pos_w1 == 66:
        return
    pos_w2 = page.find('" >компании', pos_w1)
    if pos_w2 == -1:
        return
    aid = page[pos_w1:pos_w2]
    sleep(1)
    data = requests.get(url, {'id': aid}, cookies=COOKIES_WA).text
    pos_w1 = data.find('<b>Производство:</b>')
    if pos_w1 == -1:
        return
    pos_w2 = data.find('</table>', pos_w1)
    pos_w1 = data.find("class='estimation'>", pos_w1, pos_w2) + 19
    result = []
    while pos_w1 > 18:
        result.append(decode_name(data[pos_w1:data.find('</a>', pos_w1, pos_w2)]))
        pos_w1 = data.find("class='estimation'>", pos_w1, pos_w2) + 19
    return result


def directors(page: str) -> list[dict[str, str]] | None:
    """
    Извлечение режиссёров из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Список словарей режиссёров в WA. None — если нет информации о режиссёрах.
    """
    url = f'{WAA}{AN}_full_cast.php'
    pos1 = page.find('<b>Основное</b>') + 15
    pos1 = page.find(url, pos1) + 61
    if pos1 == 60:
        return
    pos2 = page.find('" >авторы', pos1)
    if pos2 == -1:
        return
    aid = page[pos1:pos2]
    sleep(1)
    data = requests.get(url, {'id': aid}, cookies=COOKIES_WA).text
    pos1 = data.find('<b>Режиссер:</b>')
    pos2 = data.find('</table>', pos1)
    ex = data.find('режиссер эпизода/сегмента')
    if ex == -1:
        ex = pos2
    result = []
    i = 0
    while True:
        pos1 = data.find('people.php?id=', pos1, pos2) + 14
        tr = data.find('<tr>', pos1, pos2)
        if tr == -1:
            tr = pos2
        if pos1 == 13 or tr > ex:
            break
        result.append(people(int(data[pos1:data.find('" ', pos1, pos2)])))
        i += 1
    return result if len(result) else None


def notes(page: str) -> str:
    """
    Извлечение примечаний из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Примечания в WA.
    """
    pos1 = page.find('<b>Тип</b>')
    pos2 = page.find('</table>', pos1)
    pos1 = page.find(' (', pos1, pos2) + 2
    if pos1 == 1:
        return ''
    pos1 = page.find(' + ', pos1, pos2) + 1
    if pos1 == 0:
        return ''
    pos2 = page.find('), ', pos1, pos2)
    return page[pos1:pos2]


def extraction_anime(page: str, mid: int | None = None
                     ) -> dict[str, str | int | list[str] | list[dict[str, str]] | None]:
    """
    Извлечение anime из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :param mid: ID связанной манги в WA.
    :return: Словарь данных по anime в WA.
    {
        'name_orig': str,
        'name_rom': str,
        'name_eng': str,
        'name_rus': str,
        'format': str,
        'number_of_episodes': int,
        'duration': str,
        'date_of_premiere': str,
        'studio': list[str],
        'director': dict[int, dict[str, str]],
        'genre': list[str],
        'notes': str,
        'poster': str,
        'ann': int
    }
    """
    result = {
        'name_orig': title_orig(page),
        'name_rom': title_rom(page),
        'name_eng': title_eng(page),
        'name_rus': title_rus(page),
        'format': anime_format(page),
        'number_of_episodes': number_of_episodes(page),
        'duration': duration(page),
        'date_of_premiere': anime_date_of_premiere(page),
        'studio': studios(page),
        'director': directors(page),
        'genre': genres(page),
        'notes': notes(page),
        'poster': poster(page),
        'ann': ann_anime_id(page)
    }
    if result['name_rus'] == result['name_rom']:
        result['name_rus'] = ''
    if result['name_orig'] == result['name_rus'] and result['name_rom'] != '':
        result['name_orig'] = result['name_rom']
    if result['name_eng'] == '' and result['name_orig'] == result['name_rom']:
        result['name_eng'] = result['name_rom']
    if mid:
        result[M + '_id'] = mid
    return result


def search_people(name_rom: str) -> dict[str, str] | None:
    """
    Поиск персоны в WA.
    :param name_rom: Имя персоны на ромадзи или английском.
    :return: Словарь имён персоны либо None.
    """
    page = requests.get(WA + 'search.php', cookies=COOKIES_WA,
                        params={'public_search': name_rom, 'global_sector': "people"}).text
    pos = 0
    while True:
        pos = page.find("people.php?id=", pos) + 14
        if pos == 13:
            return
        id_ = int(page[pos:page.find("'", pos)])
        p = people(id_)
        if p['name_rom'] == name_rom:
            return p
