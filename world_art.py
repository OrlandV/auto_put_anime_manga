"""
Поиск страниц в World Art (далее — WA) и их обработка.
"""
from time import sleep
import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import unquote

from decode_name import points_codes, decode_name, hours_minutes
from constants import *
from config import COOKIES_WA, IGNORED_GENRES


def html(id_: int, am: bool = False, url: str | None = None) -> BeautifulSoup | None:
    """
    Получение HTML-кода страницы в WA.
    :param id_: ID в URI-параметрах.
    :param am: Переключатель: anime/манга (0/1 | False/True).
    :param url: URL раздела WA.
    :return: HTML-код страницы в WA в виде BeautifulSoup-контента либо None,
        если статус-код не входит в интервал [200, 400).
    """
    if not url:
        url = WAAM if am else WAAA
    sleep(1)
    result = requests.get(url, {'id': id_}, cookies=COOKIES_WA)
    if result.ok:
        return BeautifulSoup(result.content, "html.parser")


def anime_pages(aid: int, pages: dict[int, BeautifulSoup] = {}, aids: set[int] | list[int] | tuple[int] = []
                ) -> dict[int, BeautifulSoup] | None:
    """
    Поиск продолжений anime в WA и формирование словаря страниц.
    :param aid: ID anime в WA.
    :param pages: Словарь уже найденных страниц anime.
    :param aids: Множество, список или кортеж ID уже найденных страниц anime.
    :return: Словарь страниц в WA.
    """
    print(f"wa.anime_pages({aid})")
    page = html(aid)
    f = page.find(lambda tag: tag.name == "font" and tag.has_attr("size")
                              and tag.attrs['size'] == "2" and "Информация о серии" in tag.text)
    if not f:
        return {aid: page}
    if trs := f.find_next(
        lambda tag: tag.name == "td" and tag.has_attr("valign") and tag.attrs['valign'] == "top"
                    and tag.has_attr("width") and tag.attrs['width'] == "20" and ("#1" in tag.text or "#01" in tag.text)
    ):
        trs = trs.parent.parent.contents
        for tr in trs:
            a = tr.contents[1].a
            if "(отменённый проект)" not in a.text:
                nid = int(a.attrs['href'].split("?id=")[1])
                if nid not in pages and nid not in aids:
                    pages[nid] = page if nid == aid else html(nid)
        if len(pages):
            return pages
        return {aid: page} if "(отменённый проект)" not in a.text else None
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


def search_anime(search: str, year: int, form: str, pages: dict[int, BeautifulSoup] = {},
                 aids: set[int] | list[int] | tuple[int] = []) -> dict[int, BeautifulSoup] | None:
    """
    Поиск anime в WA.
    :param search: Наименование anime.
    :param year: Год премьеры.
    :param form: Формат.
    :param pages: Словарь уже найденных страниц anime.
    :param aids: Множество, список или кортеж ID уже найденных страниц anime.
    :return: Словарь страниц anime в WA либо None.
    """
    print(f"wa.search_anime('{search}', {year}, '{form if form else ''}')")
    search_ = points_codes(search)
    data = requests.get(WA + 'search.php', cookies=COOKIES_WA,
                        params={'public_search': search_, 'global_sector': AN}).content
    data = BeautifulSoup(data, "html.parser")
    aid = 0
    if meta := data.find("meta", {'http-equiv': "Refresh"}):
        meta = meta.attrs['content']
        aid = int(meta[meta.find("?id=") + 4:])
    else:
        ls = len(search_)
        if a := data.find(lambda tag: tag.name == "a" and tag.has_attr("class")
                                      and tag.attrs['class'] == ["review"] and search_ in tag.parent.text):
            trs = a.parent.parent.parent.contents
            if form:
                for tr in trs:
                    td_text = "\n".join(tr.strings)
                    pos = td_text.find(search_)
                    if ((td_text[pos + ls:pos + ls + 7] == "&nbsp;(" or td_text[pos + ls:pos + ls + 1] == "\n")
                            and (td_text[pos - 1:pos] == "\n" or pos == 0)):
                        pos1 = td_text.find(", Япония, ") + 10
                        pos2 = td_text.find(",", pos1)
                        if pos2 == -1:
                            pos2 = td_text.find(")", pos1)
                        if form in td_text[pos1:pos2] and str(year) in td_text[pos1 - 14:pos1 - 10]:
                            aid = int(tr.a.attrs['href'].split("?id=")[1])
                            break
            else:
                animes = []
                for tr in trs:
                    aid = int(tr.a.attrs['href'].split("?id=")[1])
                    if aid in pages or aid in aids:
                        return
                    animes.append((aid, tr.td.text))
                animes = animes[::-1]
                text = "\n0. *** Подходящего варианта нет ***"
                for i, anime in enumerate(animes):
                    text += f"\n{i + 1}. {anime[1]}"
                print(f"Укажите номер anime, подходящего под искомое наименование «{search}»:{text}")
                while True:
                    num = input("Укажите номер: ")
                    if num.isdigit():
                        break
                    print("Ошибка! Требуется ввести целое число.")
                num = int(num)
                if not num:
                    return
                aid = animes[num - 1][0]
    if aid in pages or aid in aids:
        return
    if aid:
        return anime_pages(aid, pages, aids)


def manga_pages(mid: int) -> dict[int, BeautifulSoup]:
    """
    Поиск продолжений манги в WA и формирование словаря страниц.
    :param mid: Страница манги в WA (HTML-код, возвращённый search_manga_in_anime_page).
    :return: Словарь страниц манги в WA.
    """
    print(f"- - wa.manga_pages({mid})")
    page = html(mid, True)
    f = page.find(lambda tag: tag.name == "font" and tag.has_attr("size")
                              and tag.attrs['size'] == "2" and "Эта серия состоит из" in tag.text)
    if not f:
        return {mid: page}
    trs = f.find_next(
        lambda tag: tag.name == "td" and tag.has_attr("valign") and tag.attrs['valign'] == "top"
                    and ("#1" in tag.text or "#01" in tag.text)
    ).parent.parent.contents
    res = {}
    for tr in trs:
        nid = int(tr.contents[1].a.attrs['href'].split("?id=")[1])
        res[nid] = page if nid == mid else html(nid)
    if len(res):
        return res
    return {mid: page}


def search_manga(search: str, year: int, pages: dict[int, BeautifulSoup] = {},
                 mids: set[int] | list[int] | tuple[int] = []) -> dict[int, BeautifulSoup] | None:
    """
    Поиск манги в WA.
    :param search: Наименование манги.
    :param year: Год премьеры.
    :param pages: Словарь уже найденных страниц манги.
    :param mids: Множество, список или кортеж ID уже найденных страниц манги.
    :return: Словарь страниц манги в WA.
    """
    print(f"wa.search_manga('{search}', {year})")
    search_ = points_codes(search)
    data = requests.get(WA + 'search.php', cookies=COOKIES_WA,
                        params={'public_search': search_, 'global_sector': M}).content
    data = BeautifulSoup(data, "html.parser")
    mid = 0
    if meta := data.find("meta", {'http-equiv': "Refresh"}):
        meta = meta.attrs['content']
        mid = int(meta[meta.find("?id=") + 4:])
    else:
        ls = len(search_)
        if a := data.find(lambda tag: tag.name == "a" and tag.has_attr("class")
                                      and tag.attrs['class'] == ["review"] and search_ in tag.parent.text):
            trs = a.parent.parent.parent.contents
            for tr in trs:
                td_text = "\n".join(tr.strings)
                pos = td_text.find(search_)
                if ((td_text[pos + ls:pos + ls + 7] == "&nbsp;(" or td_text[pos + ls:pos + ls + 1] == "\n")
                        and (td_text[pos - 1:pos] == "\n" or pos == 0) and str(year) in tr.a.text[-5:-1]):
                    mid = int(tr.a.attrs['href'].split("?id=")[1])
                    break
    if mid in pages or mid in mids:
        return
    return manga_pages(mid) if mid else None


def manga_pages_from_anime(
        wa_manga_pages: dict[int, BeautifulSoup] | None, wa_anime_pages: dict[int, BeautifulSoup] | None
) -> tuple[dict[int, BeautifulSoup], dict[int, int]]:
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
        if f := manga.find(lambda tag: tag.name == "font" and tag.has_attr("size") and tag.attrs['size'] == "2"
                                       and "Эта серия состоит из" in tag.text):
            trs = f.find_next(
                lambda tag: tag.name == "td" and tag.has_attr("valign") and tag.attrs['valign'] == "top"
                            and ("#1" in tag.text or "#01" in tag.text)
            ).parent.parent.contents
            for tr in trs:
                a = tr.contents[1].a or tr.contents[2].a
                nid = int(a.attrs['href'].split("?id=")[1])
                if nid not in wa_manga_pages:
                    related_manga(nid)

    print("wa.manga_pages_from_anime(wa_manga_pages, wa_anime_pages)")
    rm = {}
    for aid, anime in wa_anime_pages.items():
        td = anime.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                                    and "Снято по манге" in tag.text)
        if td:
            mid = int(td.next_sibling.next_sibling.a.attrs['href'].split("?id=")[1])
            if not wa_manga_pages or mid not in wa_manga_pages:
                related_manga(mid)
            rm[aid] = mid
    return wa_manga_pages, rm


def related_anime(wa_anime_pages: dict[int, BeautifulSoup], aid: int) -> dict[int, BeautifulSoup]:
    """
    Поиск связанного anime в WA и добавление его в словарь страниц anime в WA.
    :param wa_anime_pages: Словарь страниц anime в WA.
    :param aid: ID anime в WA.
    :return: Обновлённый словарь страниц anime в WA.
    """
    anime = html(aid)
    wa_anime_pages[aid] = anime
    f = anime.find(lambda tag: tag.name == "font" and tag.has_attr("size")
                               and tag.attrs['size'] == "2" and "Информация о серии" in tag.text)
    if not f:
        return wa_anime_pages
    trs = f.find_next(
        lambda tag: tag.name == "td" and tag.has_attr("valign") and tag.attrs['valign'] == "top"
                    and tag.has_attr("width") and tag.attrs['width'] == "20" and ("#1" in tag.text or "#01" in tag.text)
    ).parent.parent.contents
    for tr in trs:
        nid = int(tr.contents[1].a.attrs['href'].split("?id=")[1])
        if nid not in wa_anime_pages:
            wa_anime_pages = related_anime(wa_anime_pages, nid)
    return wa_anime_pages


def anime_id_from_manga(page: BeautifulSoup) -> list[int | None]:
    """
    Извлечение ID anime в WA из страницы манги в WA и формирование списка.
    :param page: Страница манги (HTML-код) в WA.
    :return: Список ID anime в WA.
    """
    f = page.find(lambda tag: tag.name == "font" and tag.has_attr("size")
                              and tag.attrs['size'] == "2" and "По этой манге снято аниме" in tag.text)
    if not f:
        return []
    trs = f.find_next(
        lambda tag: tag.name == "td" and tag.has_attr("valign") and tag.attrs['valign'] == "top"
                    and ("#1" in tag.text or "#01" in tag.text)
    ).parent.parent.contents
    return [int(tr.contents[2].a.attrs['href'].split("?id=")[1]) for tr in trs
            if "(отменённый проект)" not in tr.contents[2].a.text]


def anime_pages_from_manga(wa_anime_pages: dict[int, BeautifulSoup], wa_manga_pages: dict[int, BeautifulSoup]
                           ) -> dict[int, BeautifulSoup]:
    """
    Добавление anime, связанных с мангой из словаря страниц манги в WA, в словарь страниц anime в WA.
    :param wa_anime_pages: Словарь страниц anime в WA.
    :param wa_manga_pages: Словарь страниц манги в WA.
    :return: Обновлённый словарь страниц anime в WA.
    """
    print("wa.anime_pages_from_manga(wa_anime_pages, wa_manga_pages)")
    for manga in wa_manga_pages.values():
        aids = anime_id_from_manga(manga)
        if len(aids):
            for aid in aids:
                if aid not in wa_anime_pages:
                    wa_anime_pages = related_anime(wa_anime_pages, aid)
    return wa_anime_pages


def ann_anime_id(wa_page: BeautifulSoup) -> int | None:
    """
    Извлечение ID anime в ANN по ссылке в WA.
    :param wa_page: Страница anime (HTML-код) в WA.
    :return: ID anime в ANN, если найдена ссылка в WA. Иначе — None.
    """
    td = wa_page.find(lambda tag: tag.name == "td" and tag.has_attr("class")
                                  and tag.attrs['class'] == ["bg2"] and "Сайты" in tag.text)
    ni = td.parent.parent.find_next_sibling("noindex")
    if a := ni.find_next(lambda tag: tag.name == "a" and f"{SANNE}{A}.php" in tag.attrs['href']):
        return int(a.attrs['href'].split("?id=")[1])


def ann_manga_id(wa_page: BeautifulSoup) -> int | None:
    """
    Извлечение ID манги в ANN по ссылке в WA.
    :param wa_page: Страница манги (HTML-код) в WA.
    :return: ID манги в ANN, если найдена ссылка в WA. Иначе — None.
    """
    if td := wa_page.find(lambda tag: tag.name == "td" and tag.has_attr("class")
                                      and tag.attrs['class'] == ["review"] and "Сайты" in tag.text):
        a = td.next_sibling.next_sibling.find_next(lambda tag: tag.name == "a" and tag.text == "ann")
        return int(a.attrs['href'].split("?id=")[1]) if a else None


def wp_anime_title(wa_page: BeautifulSoup) -> str | None:
    """
    Извлечение заголовка anime в WP по ссылке в WA.
    :param wa_page: Страница (HTML-код) в WA.
    :return: Заголовок в WP, если найдена ссылка в WA. Иначе — None.
    """
    if td := wa_page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["bg2"]
                                      and "Википедия" in tag.text):
        ni = td.parent.parent.find_next_sibling("noindex")
        url = ni.a.attrs['href']
        return unquote(url[url.find("/wiki/") + 6:])


def wp_manga_title(wa_page: BeautifulSoup) -> str | None:
    """
    Извлечение заголовка манги в WP по ссылке в WA.
    :param wa_page: Страница (HTML-код) в WA.
    :return: Заголовок в WP, если найдена ссылка в WA. Иначе — None.
    """
    td = wa_page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                                  and "Вики" in tag.text).next_sibling.next_sibling.contents
    for a in td:
        if isinstance(a, Tag) and a.has_attr("href") and a.text == "вики (en)":
            return unquote(a.attrs['href'][a.attrs['href'].find("/wiki/") + 6:])


# def mu_manga_id(wa_page: BeautifulSoup) -> int | None:
#     """
#     Поиск ID манги в MU по ссылке в WA.
#     :param wa_page: Страница манги (HTML-код) в WA.
#     :return: ID манги в MU, если найдена ссылка в WA. Иначе — None.
#     """
#     print("- wa.mu_manga_id(wa_page)")
#     pos = wa_page.find(WMU) + 43
#     if pos == 42:
#         return
#     pos2 = wa_page.find("' ", pos)
#     heads = HEADERS.copy()
#     heads.update({'Accept-Language': 'en-US,en;q=0.9,en-EN;q=0.8,en;q=0.7'})
#     sleep(1)
#     try:
#         req = requests.get(WMU, {'id': wa_page[pos:pos2]}, headers=heads)
#         page = req.text
#     except requests.exceptions.ConnectionError:
#         print("Ошибка подключения к", WMU)
#         return
#     except requests.exceptions.ReadTimeout:
#         print(f"Время ожидания соединения с {WMU} истекло.")
#         return
#     if not page:
#         print(WMU, "вернул", req.status_code)
#         return
#     pos = page.find('"identifier":') + 13
#     pos2 = page.find(',', pos)
#     return int(page[pos:pos2])


def title_rom(page: BeautifulSoup, am: bool = False) -> str:
    """
    Извлечение ромадзи наименования из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :param am: Переключатель: anime/манга (False/True).
    :return: Ромадзи наименование в WA.
    """
    td = page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                               and f"Названи{"я" if am else "е"} (ромадзи)" in tag.text)
    if not td:
        td = page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                                   and "Названия (яп.)" in tag.text)
    if td:
        td = td.next_sibling.next_sibling
    else:
        td = page.find(lambda tag: tag.name == "font" and tag.has_attr("size") and tag.attrs['size'] == "5")
    return td.text.replace(' - ', ' — ').replace('...', '…')


def title_rus(page: BeautifulSoup) -> str:
    """
    Извлечение русского наименования из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Русское наименование в WA.
    """
    td = page.find(lambda tag: tag.name == "font" and tag.has_attr("size") and tag.attrs['size'] == "5")
    return td.text.replace(' - ', ' — ').replace('...', '…')


def title_orig(page: BeautifulSoup, am: bool = False) -> str:
    """
    Извлечение оригинального наименования из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :param am: Переключатель: anime/манга (False/True).
    :return: Оригинальное наименование в WA.
    """
    if tds := page.find_all(
        lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                    and (f"Названи{"я" if am else "е"} (кандзи)" in tag.text or "Названия (прочие)" in tag.text
                         or "Названия (яп.)" in tag.text)
    ):
        if len(tds) == 1:
            return tds[0].next_sibling.next_sibling.text
        titles = []
        text = f"\n0. *** Подходящего варианта нет ***"
        for i, td in enumerate(tds):
            title = td.next_sibling.next_sibling.text
            titles.append(title)
            text += f"\n{i + 1}. {title}"
        print(f"Выберите оригинальное наименование манги:{text}")
        while True:
            num = input("Укажите номер: ")
            if num.isdigit():
                num = int(num)
                break
            print("Ошибка! Требуется ввести целое число.")
        if not num:
            return ""
        return titles[num - 1]


def manga_title_r(func, *args) -> str:
    """
    Удаление в наименовании окончания « (манга)».
    :param func: Функция title_rom или title_rus.
    :param args: аргументы функций title_rom или title_rus.
    :return: Исправленное наименование.
    """
    manga_title = func(*args)
    return manga_title.removesuffix(' (манга)')


def title_eng(page: BeautifulSoup, am: bool = False) -> str | None:
    """
    Извлечение английского наименования из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :param am: Переключатель: anime/манга (False/True).
    :return: Английское наименование в WA.
    """
    if td := page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                                   and f"Названи{"я" if am else "е"} (англ.)" in tag.text):
        return td.next_sibling.next_sibling.text.replace(' - ', ' — ').replace('...', '…')


def people(pid: int) -> dict[str, str]:
    """
    Извлечение имён персоны из страницы в WA.
    :param pid: ID персоны в WA.
    :return: Словарь имён персоны в WA.
    """
    page = html(pid, url=f"{WA}people.php")
    f = page.find(lambda tag: tag.name == "font" and tag.has_attr("size") and tag.attrs['size'] == "5").text
    res = {'name_rus': f}
    f = page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                              and "Имя по-английски" in tag.text).next_sibling.next_sibling.text
    res['name_rom'] = f
    f = page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                              and "Оригинальное имя" in tag.text)
    res['name_orig'] = f.next_sibling.next_sibling.text if f else res['name_rom']
    return res


def authors(page: BeautifulSoup) -> dict[int, dict[str, str]]:
    """
    Извлечение имён авторов из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Словарь авторов — словарей имён авторов (персон) в WA.
    """
    td = page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                               and "Авторы" in tag.text).next_sibling.next_sibling.contents
    res = {}
    for a in td:
        if isinstance(a, Tag) and a.has_attr("href"):
            id_ = int(a.attrs['href'].split("?id=")[1])
            res[id_] = people(id_)
    return res


def manga_date_of_premiere(page: BeautifulSoup, full_format: bool = True) -> str:
    """
    Извлечение даты премьеры манги из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :param full_format: Флаг полного формата даты (гггг.мм.дд). Если False, то только год (гггг).
    :return: Дата премьеры манги в WA.
    """
    td = page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                               and "Год выпуска" in tag.text).next_sibling.next_sibling
    return td.text + ("-12-31" if full_format else "")


def publication(page: BeautifulSoup) -> dict[int, dict[str, str]]:
    """
    Извлечение изданий из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Словарь изданий в WA.
    """
    td = page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                               and "Сериализация" in tag.text).next_sibling.next_sibling.contents
    res = {}
    for a in td:
        if isinstance(a, Tag) and a.has_attr("href"):
            id_ = int(a.attrs['href'].split("?id=")[1])
            page_ = html(id_, url=f"{WA}company.php")
            c = page_.find(lambda tag: tag.name == "a" and tag.has_attr("href")
                                       and "company.php" in tag.attrs['href']).text
            if c == "Morning":
                c = "Shuukan Morning"
            elif c == "Kadokawa":
                c = "Kadokawa Shoten"
            res[id_] = {'publication': a.text, 'publishing': c}
            if res[id_]['publishing'] == "Futabasha" and res[id_]['publication'] == "Manga Action":
                res[id_]['publication'] = "Shuukan Manga Action"
            elif res[id_]['publishing'] == "Kadokawa Shoten" and res[id_]['publication'] == "Asuka":
                res[id_]['publication'] = "Gekkan Asuka"
    return res


def genres(page: BeautifulSoup) -> list[str]:
    """
    Извлечение жанров из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Список жанров в WA.
    """
    td = page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                               and "Жанр" in tag.text).next_sibling.next_sibling.contents
    return [a.text for a in td if isinstance(a, Tag) and a.has_attr("href") and a.text not in IGNORED_GENRES]


def poster(page: BeautifulSoup, am: bool = False) -> str | None:
    """
    Извлечение URL постера из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :param am: Переключатель: anime/манга (False/True).
    :return: URL постера в WA.
    """
    if a := page.find(lambda tag: tag.name == "a" and ("img/" if am else "_poster.php?id=") in tag.attrs['href']):
        if not am and not a.img:
            a = a.find_next(lambda tag: tag.name == "a" and ("img/" if am else "_poster.php?id=") in tag.attrs['href'])
        return WAA + a.attrs['href'] if am else a.img.attrs['src']


def extraction_manga(page: BeautifulSoup) -> dict[str, str | dict[int, dict[str, str]] | dict[int, str] | list[str]]:
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
        'poster': str,
        'ann': int
    }
    """
    print("- wa.extraction_manga(page):", end=" ")
    result = {
        'name_orig': title_orig(page, True),
        'name_rom': manga_title_r(title_rom, page, True),
        'name_eng': title_eng(page, True),
        'name_rus': manga_title_r(title_rus, page),
        'author_of_manga': authors(page),
        'date_of_premiere': manga_date_of_premiere(page),
        'publication': publication(page),
        'genre': genres(page),
        'poster': poster(page, True),
        'ann': ann_manga_id(page)
    }
    if result['name_rus'] == result['name_rom']:
        result['name_rus'] = ''
    if not result['name_eng'] and result['name_orig'] == result['name_rom']:
        result['name_eng'] = result['name_rom']
    elif not result['name_rus'] and result['name_eng'] and result['name_rom']:
        result['name_rus'] = result['name_rom']
        result['name_rom'] = result['name_eng']
    print(result['name_rom'])
    return result


def anime_format(page: BeautifulSoup) -> str | None:
    """
    Извлечение формата anime из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Формат anime в WA.
    """
    td = page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                               and "Тип" in tag.text)
    if td:
        td = td.next_sibling.next_sibling.text
        pos = td.find(" (")
        if pos == -1:
            pos = td.find(",")
        return td[:pos]


def number_of_episodes(page: BeautifulSoup) -> int:
    """
    Извлечение количества эпизодов из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Количество эпизодов в WA.
    """
    td = page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                               and "Тип" in tag.text)
    if td:
        td = td.next_sibling.next_sibling.text
        pos = td.find(" (") + 2
        if pos == 1:
            return 1
        pos2 = td.find(" эп.", pos)
        return int(td[pos:pos2])


def duration(page: BeautifulSoup) -> str | None:
    """
    Извлечение продолжительности эпизода из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Продолжительность эпизода в формате чч:мм в WA.
    """
    td = page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                               and "Тип" in tag.text)
    if td:
        td = td.next_sibling.next_sibling.text
        pos = td.find("), ") + 3
        if pos == 2:
            pos = td.find(", ") + 2
        pos2 = td.find(" мин.", pos)
        return hours_minutes(int(td[pos:pos2]))


def anime_date_of_premiere(page: BeautifulSoup) -> str | None:
    """
    Извлечение даты премьеры anime из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Дата премьеры anime в WA.
    """
    td = page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                               and ("Выпуск" in tag.text or "Премьера" in tag.text))
    if td:
        a = td.next_sibling.next_sibling.a
        res = ""
        for i in range(3):
            res = a.text + ("-" + res if i > 0 else "")
            a = a.find_next_sibling("a")
        return res


def studios(page: BeautifulSoup) -> list[str] | None:
    """
    Извлечение студий из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Список наименований студий в WA. None — если нет информации о студиях.
    """
    if (page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["bg2"]
                              and "Основное" in tag.text)
            and (a := page.find(lambda tag: tag.name == "a" and "компании" in tag.text))):
        a = a.attrs['href'].split("?id=")
        page = html(int(a[1]), url=a[0])
        if f := page.find(lambda tag: tag.name == "font" and "Производство:" in tag.text):
            trs = f.parent.parent.parent.contents
            return [decode_name(trs[tr].a.text) for tr in range(len(trs)) if tr]


def directors(page: BeautifulSoup) -> list[dict[str, str]] | None:
    """
    Извлечение режиссёров из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Список словарей режиссёров в WA. None — если нет информации о режиссёрах.
    """
    if (page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["bg2"]
                              and "Основное" in tag.text)
            and (a := page.find(lambda tag: tag.name == "a" and "авторы" in tag.text))):
        a = a.attrs['href'].split("?id=")
        page = html(int(a[1]), url=a[0])
        if f := page.find(lambda tag: tag.name == "font" and "Режиссер:" in tag.text):
            trs = f.parent.parent.parent.contents
            res = []
            d1 = False
            for tr in range(len(trs)):
                if tr:
                    tds = trs[tr].contents
                    if len(tds) > 2 and not tds[2].td:
                        d1 = True
                    a = tds[1].a.attrs['href'].split("?id=")
                    res.append(people(int(a[1])))
                    if d1:
                        break
            return res


def notes(page: BeautifulSoup) -> str:
    """
    Извлечение примечаний из страницы в WA.
    :param page: Страница (HTML-код) в WA.
    :return: Примечания в WA.
    """
    td = page.find(lambda tag: tag.name == "td" and tag.has_attr("class") and tag.attrs['class'] == ["review"]
                               and "Тип" in tag.text)
    if td:
        td = td.next_sibling.next_sibling.text
        pos = td.find(" (") + 2
        if pos == 1:
            return ""
        pos = td.find(" + ", pos) + 1
        if pos == 0:
            return ""
        pos2 = td.find("), ", pos)
        return td[pos:pos2]


def extraction_anime(page: BeautifulSoup, mid: int | None = None
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
    print("- wa.extraction_anime(page):", end=" ")
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
    if result['name_orig'] == result['name_rus'] and result['name_rom']:
        result['name_orig'] = result['name_rom']
    if not result['name_eng'] and result['name_orig'] == result['name_rom']:
        result['name_eng'] = result['name_rom']
    if mid:
        result[M + '_id'] = mid
    print(result['name_rom'])
    return result


def search_people(name_rom: str) -> dict[str, str] | None:
    """
    Поиск персоны в WA.
    :param name_rom: Имя персоны на ромадзи или английском.
    :return: Словарь имён персоны либо None.
    """
    page = requests.get(WA + 'search.php', cookies=COOKIES_WA,
                        params={'public_search': name_rom, 'global_sector': "people"}).content
    page = BeautifulSoup(page, "html.parser")
    if meta := page.find("meta", {'http-equiv': "Refresh"}):
        meta = meta.attrs['content']
        pid = int(meta[meta.find("?id=") + 4:])
        return people(pid)
    else:
        trs = page.find(lambda tag: tag.name == "a" and tag.has_attr("href")
                                    and "people.php?id=" in tag.attrs['href']).parent.parent.parent.contents
        for tr in trs:
            p = people(int(tr.a.attrs['href'].split("?id=")[1]))
            if p['name_rom'] == name_rom:
                return p
