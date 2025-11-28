"""
Поиск страниц в Wikipedia (en) (далее — WP) и их обработка.
"""
from time import sleep
import requests
import wikipedia
import dateutil.parser as date_parser

import decode_name as dn
from constants import *
from config import FORM_WP, frequency

CIS = 'class="infobox-subheader"'

wikipedia.API_URL = 'https://en.wikipedia.org/w/api.php'
wikipedia.set_user_agent(USER_AGENT)


def page(url: str) -> str | None:
    """
    Получение HTML-кода страницы по внутренней ссылке в WP. Используется пакет requests.
    :param url: Внутренняя ссылка (после /wiki/).
    :return: HTML-код страницы или None, если статус-код не равен 200.
    """
    sleep(1)
    result = requests.get(
        WPES + url,
        headers={'User-Agent': USER_AGENT}
    )
    if result.status_code == 200:
        return dn.decode_name(result.text)


class Page:
    """
    Страница из Wikipedia (en).

    Свойства:
    html — HTML-код страницы (или None, если статус-код не равен 200);
    url — внутренняя ссылка (после /wiki/).
    """
    def __init__(self, search: str):
        """
        Получение страницы (HTML-кода) из WP. Используется пакет wikipedia.
        Если в течение ~15 секунд нет результата, происходит переключение на page, а пробелы в search заменяются на «_».
        :param search: Искомое наименование.
        """
        b = 0
        while True:
            sleep(1)
            try:
                for wpt in wikipedia.search(search):
                    if dn.normal_name(wpt) == dn.normal_name(search):
                        wp = wikipedia.WikipediaPage(wpt, redirect=True, preload=False)
                        self.html = dn.decode_name(wp.html())
                        self.url = wp.url.removeprefix(WPE).removeprefix(WPES)
                        break
                else:
                    self._try_page(search)
                break
            except wikipedia.WikipediaException:
                b += 1
                if b == 15:
                    self._try_page(search)
                    break

    def _try_page(self, search: str):
        url = search.replace(' ', '_')
        self.html = page(url)
        self.url = url


def _pos_table(_page: str) -> int:
    """
    Поиск инфо-бокса.
    :param _page: HTML-код.
    :return: Позиция инфо-бокса. (Позиция после «<table ».)
    """
    post = _page.find('<table') + 7
    for box in ('class="box-Lead_too_short', 'class="box-Multiple_issues',
                'class="box-More_citations_needed', 'class="box-In-universe'):
        if _page.find(box, post) != -1:
            post = _page.find('<table', post) + 7
    return post


def _pos_ab(_page: str, a: int, b: int) -> tuple[int, int]:
    """
    Поиск текста между HTML-тегами.
    :param _page: HTML-код.
    :param a: Позиция начала поиска.
    :param b: Позиция конца поиска.
    :return: Позиции начала и конца текста.
    """
    posa = _page.find('>', a, b) + 1
    posb = _page.find('<', posa, b)
    while posa != b and (posa == posb or posa == posb + 1 or len(_page[posa:posb].strip()) < 4):
        posa = _page.find('>', posa, b) + 1
        posb = _page.find('<', posa, b)
    if "<style " in _page[_page.find("<", posa - 57, posa - 1):posa]:
        return _pos_ab(_page, posb, b)
    if posb < 0:
        posb = b
    return posa, posb


def search_pages(search: str, res: dict[str, str] = {}) -> dict[str, str]:
    """
    Поиск страниц по наименованию в WP.
    :param search: Искомое наименование.
    :param res: Дополняемый словарь {title: HTML} страниц в WP.
    :return: Итоговый словарь {title: HTML} страниц в WP.
    """
    def res_update(post: int, posl: int) -> None:
        nonlocal res
        if _page.html.find('<i>', post, posl) != -1:
            while True:
                post = _page.html.find('title="', post, posl) + 7
                if post == 6:
                    break
                ttl = _page.html[post:_page.html.find('"', post, posl)]
                if ttl not in res:
                    res = search_pages(ttl, res)

    def res_update_ul() -> None:
        posu = _page.html.find('<ul>', pos, pos2) + 4
        if posu != 3:
            res_update(posu, _page.html.find('</ul>', posu, pos2))

    print(f"- wp.search_pages('{search}')")
    search_ = dn.normal_name(search)
    _page = Page(search)
    if _page.html:
        norm_page = dn.normal_name(_page.html)
    if (not _page.html or
            '<div class="shortdescription nomobile noexcerpt noprint searchaux" style="display:none">'
            'Name list</div>' in _page.html or
            (M not in search_ and search_ not in norm_page) or
            (M in search_ and search_[:-6] not in norm_page)):
        return res
    res[_page.url.replace('_', ' ')] = _page.html
    posb = _pos_table(_page.html)
    pose = _page.html.find('</table>', posb)
    pos = _page.html.find('<link ', posb, pose)
    if pos != -1:
        pos1 = _page.html.find(CIS, posb, pose) + 25
        pos1 = _page.html.find(CIS, pos1, pose) + 25
        while pos1 > 24 and pos > 0:
            pos2 = _page.html.find(CIS, pos1, pose)
            if pos2 == -1:
                pos2 = pose
            if pos2 > pos:
                pos, posa = _pos_ab(_page.html, pos1, pos2)
                if pos == 0:
                    break
                t = _page.html[pos:posa]
                if 'anim' in t.lower() or 'Manga' in t:
                    res_update_ul()
                elif t in ('Related series', 'Feature films', 'Related works'):
                    poso = _page.html.find('<ol>', pos, pos2) + 4
                    if poso != 3:
                        res_update(poso, _page.html.find('</ol>', poso, pos2))
                    else:
                        res_update_ul()
            pos1 = pos2 + 25
            pos = _page.html.find('<link ', pos1, pose)
    return res


def manga_anime_in_page(pages: dict[str, str]) -> dict[str, dict[str, dict[str, str]]]:
    """
    Извлечение из страницы частей страницы (частей инфо-блоков) по отдельным манге и anime в WP.
    :param pages: Словарь страниц (HTML-код) в WP.
    :return: Словарь:
    {
        page_title: {
            'manga': {
                manga_title: page_part,

                ...
            },

            'anime': {
                anime_title: page_part,

                ...
            }
        }
    }
    """
    print("- wp.manga_anime_in_page(pages):")
    result = {}
    for page_title, _page in pages.items():
        print("- - ", page_title)
        res = {}
        posb = _pos_table(_page)
        pose = _page.find('</table>', posb)
        pos1 = _page.find(CIS, posb, pose)
        if pos1 != -1:
            l1 = 25
            v2 = False
            pos1 = _page.find(CIS, pos1 + l1, pose)
        else:
            l1 = 29
            v2 = True
            pos1 = _page.find('class="infobox-above summary"', posb, pose)
        while (pos1 > l1 - 1) and pos1 < pose:
            pos2 = _page.find(CIS, pos1 + l1, pose)
            if pos2 == -1:
                pos2 = _page.find('TemplateStyles:r1316064257', pos1 + l1, pose)
            if pos2 == -1:
                pos2 = pose
            if 'class="infobox-full-data"' not in _page[pos1:pos2]:
                pos, posa = _pos_ab(_page, pos1, pos2)
                if pos == 0 or posa < 0:
                    break
                t = _page[pos:posa]
                if 'Manga' in t or 'anim' in t.lower():
                    posa = _page.find('class="infobox-header" style="background:#EEF;', pos1, pos2)
                    if posa > 0:
                        posa, posb = _pos_ab(_page, posa, pos2)
                        ttl = _page[posa:posb]
                    else:
                        ttl = page_title.removesuffix(" (manga)")
                    am = M if 'Manga' in t else A
                    if am not in res:
                        res[am] = {}
                    if ttl in res[am]:
                        ttl += f' ({t})'
                    res[am][ttl] = _page[pos:pos2]
                elif v2:
                    page_part = _page[pos:pos2]
                    t = page_part[:page_part.find("</th>")].replace("</i>", " ").replace("<br />", " ")
                    am = A if '>Directed by</th>' in page_part else M
                    if am not in res:
                        res[am] = {}
                    res[am][t] = page_part
                    break
            pos1 = pos2
        result[page_title] = res
    return result


def date_of_premiere(page_part: str) -> str | None:
    """
    Извлечение даты премьеры из части страницы в WP.
    :param page_part: Часть страницы (HTML-код) в WP.
    :return: Дата премьеры в WP либо None.
    """
    v2 = False
    for th in ('<th scope="row" class="infobox-label">Released</th><td ',
               '<th scope="row" class="infobox-label">Original run</th><td ',
               '<th scope="row" class="infobox-label">Published</th><td ',
               '<th scope="row" class="infobox-label">Release</th><td ',
               '>Release date</div></th>'):
        pos1 = page_part.find(th)
        if pos1 > 0:
            pos1 += len(th)
            if th == '>Release date</div></th>':
                v2 = True
                pos1 = page_part.find('<', pos1)
            break
    else:
        return
    pose = page_part.find('</td>', pos1)
    pos1, pos = _pos_ab(page_part, pos1, pose)
    if not v2:
        posa = page_part.find('</span>', pos1, pose)
        posb = page_part.find('<span', pos1, pose)
        pos2 = min(posa, posb)
        if pos2 < 0:
            pos2 = page_part.find('<', pos1, pose)
        if pos2 < 0:
            pos2 = pose
    else:
        pos2 = pos
    date = page_part[pos1:pos2].strip()
    if len(date) == 4:
        return date_parser.parse(date).strftime('%Y') + '-12-31'
    date_ = date.split(' ')
    if len(date_) == 2 and ((date_[0].isdigit() and len(date_[0]) == 4) or (date_[1].isdigit() and len(date_[1]) == 4)):
        return dn.month(date)
    elif len(date_) == 2:
        pos2 = page_part.find('</span>', pos1, pose)
        if pos2 != -1 and 'start' in page_part[pos1:pos2]:
            while pos < pos2:
                pos1 = page_part.find('>', pos1, pose) + 1
                pos = page_part.find('<', pos1, pose)
            return page_part[pos1:pos2].strip()
    return date_parser.parse(date).strftime('%Y-%m-%d')


def filter_page_parts(pages: dict[str, dict[str, dict[str, str]]]) -> dict[str, dict[str, dict[str, str]]]:
    """
    Фильтр частей страниц, удаляющий повторы, и переформатирование словаря частей страниц.
    :param pages: Словарь частей страниц — результат manga_anime_in_page.
    :return: Словарь
    {
        'manga': {
            title: {
                'page_part': str,

                'page_title': str
            },

            ...
        },

        'anime': {
            title: {
                'page_part': str,

                'page_title': str
            },

            ...
        }
    }
    """
    print("- wp.filter_page_parts(pages):")
    res = {}
    for page_title, _page in pages.items():
        print("- - ", page_title)
        for am, page_parts in _page.items():
            print("- " * 3, am)
            if am not in res:
                res[am] = {}
            for ttl, page_part in page_parts.items():
                print("- " * 4, ttl)
                fpp = True
                for pp in res[am].values():
                    if pp == page_part:
                        fpp = False
                        break
                if fpp:
                    if am == A:
                        ttl = ttl.replace(' (Original video animation)', ' (OVA)')
                    ttl += f' ({date_of_premiere(page_part)})'
                    res[am][dn.title_index(res[am], ttl)] = {'page_part': page_part, 'page_title': page_title}
    return res


def _count_li(_page: str, pos1: int, pos2: int) -> int:
    """
    Счётчик тега <li> в указанном отрезке строки HTML-кода.
    :param _page: Строка HTML-кода.
    :param pos1: Начало отрезка поиска.
    :param pos2: Конец отрезка поиска.
    :return: Количество тегов <li>.
    """
    res = -1
    while pos1 > 3:
        res += 1
        pos1 = _page.find('<li>', pos1, pos2) + 4
    return res


def number_of_chapters(page_part: str) -> int:
    """
    Извлечение количества глав манги из соответствующей части инфо-блока в WP.
    :param page_part: Часть страницы манги в WP (HTML-код).
    :return: Количество глав манги в WP. 0 — нет данных.
    """
    pos = page_part.find('<tr><th scope="row" class="infobox-label">Volumes</th>') + 54
    posb = page_part.find('</td></tr>', pos)
    pos = page_part.find('<a href="/wiki/', pos, posb) + 15
    if pos == 14:
        return 0
    vol_page = page(page_part[pos:page_part.find('"', pos, posb)])
    pos = vol_page.find('<h2 id="Volume_list">Volume list</h2>') + 37
    posb = vol_page.find('<div class="mw-heading mw-heading2">', pos)
    return _count_li(vol_page, pos, posb)


def number_of_chapters_2(_page: str) -> int:
    """
    Извлечение количества глав манги из страницы манги в WP.
    :param _page: Страница манги в WP (HTML-код).
    :return: Количество глав манги в WP. 0 — нет данных.
    """
    pos = _page.find('<h4 id="Chapter_list">Chapter list</h4>') + 39
    if pos == 38:
        return 0
    pos = _page.find('<table', pos)
    posf = _page.find('</table>', pos)
    return _count_li(_page, pos, posf)


def title(page_part: str) -> str:
    """
    Извлечение наименования (англ.) из соответствующей части инфо-блока в WP.
    :param page_part: Часть страницы в WP (HTML-код).
    :return: Наименование (англ.) в WP.
    """
    pos = page_part.find('<tr><th colspan="2" class="infobox-header" style="background:#EEF; font-weight:normal;"><i>'
                         ) + 91
    if pos == 90:
        return ""
    pos2 = page_part.find('</i></th></tr>', pos)
    pos1 = page_part.find('<', pos, pos2)
    if pos1 != -1:
        res = page_part[pos:pos1]
        if '<style ' in page_part[pos1:pos2]:
            pos = page_part.find('</style>', pos1, pos2) + 8
        if '<span ' in page_part[pos:pos2]:
            pos = page_part.find('>', pos, pos2) + 1
            pos_ = page_part.find('</span>', pos, pos2)
            res += page_part[pos:pos_]
            res += page_part[pos_ + 7:pos2]
        return res.strip()
    return page_part[pos:pos2]


def authors(page_part: str, *args) -> list[dict[str, str] | None]:
    """
    Извлечение имён авторов манги или режиссёров anime из соответствующей части инфо-блока в WP.
    :param page_part: Часть страницы манги в WP (HTML-код).
    :param args: Кортеж категорий авторов ("Written", "Illustrated", "Directed").
    :return: Список словарей имён авторов манги или режиссёров anime в WP.
    """
    def normal_rom(_name: str) -> str:
        """
        Нормализация ромадзи имени.
        :param _name: Ромадзи (английское) имя из страницы как есть.
        :return: Нормализованное ромадзи имя.
        """
        _name = _name.split()
        return dn.o_ou(dn.decode_name((_name[1] + " " if len(_name) > 1 else "") + _name[0])).lower().title()

    def orig_rom(_name: str) -> None:
        """
        Извлечение оригинального и ромадзи имён из HTML-страницы автора в WP и добавление в список result.
        :param _name: Ромадзи (английское) имя из страницы как есть.
        """
        apage = Page(dn.normal_name(_name)).html
        if apage:
            _pos1 = apage.find('<tr><th colspan="2" class="infobox-above')
            _name_rom = ""
            if _pos1 > 0:
                _pos1, _pos2 = _pos_ab(apage, _pos1 + 40, apage.find("</tr>", _pos1))
                _name_rom = normal_rom(apage[_pos1:_pos2])
            _name_orig = ""
            if (_pos1 := apage.find(f'<tr><td colspan="2" {CIS} style="font-size:125%;">'
                                    '<div class="nickname" lang="ja">') + 102) > 101:
                _name_orig = apage[_pos1:apage.find("</div", _pos1)]
            elif (_pos1 := apage.find('<span lang="ja">') + 16) > 15:
                _pos2 = apage.find("</span>", _pos1)
                _pos = apage.find(" (", _pos1, _pos2)
                _name_orig = apage[_pos1:_pos] if _pos != -1 else apage[_pos1:_pos2]
                while '<' in _name_orig:
                    _pos1 = _name_orig.find('<')
                    _pos2 = _name_orig.find('>', _pos1) + 1
                    _name_orig = _name_orig[:_pos1] + _name_orig[_pos2:]
                if not _name_rom:
                    _pos1 = apage.find('<i lang="ja-Latn">', _pos1) + 18
                    _name_rom = apage[_pos1:apage.find('</i>', _pos1)]
            else:
                _pos1 = apage.find("</b> (") + 6
                _pos2 = apage.find(" <", _pos1)
                _name_orig = apage[_pos1:_pos2]
                _pos1 = _pos2 + 4
                _pos2 = apage.find("<", _pos1)
                _name_rom = apage[_pos1:_pos2]
            result.append({'name_orig': _name_orig, 'name_rom': _name_rom})
        else:
            result.append({'name_rom': normal_rom(_name)})

    result = []
    for staff in args:
        pos, posa, posb = 0, 0, 0
        st = f'<tr><th scope="row" class="infobox-label">{staff} by</th><td class="infobox-data">'
        posa = page_part.find(st, posa)
        if posa == -1:
            continue
        lst = len(st)
        posb = page_part.find("</td></tr>", posa)
        pos1 = page_part.find('<ul>', posa, posb) + 4
        if pos1 > 3:
            pos2 = page_part.find('</ul>', pos1, posb)
            pos1 = page_part.find('<li>', pos1, pos2) + 4
            while pos1 > 3:
                if '<a ' in page_part[pos1:pos1 + 3]:
                    pos = page_part.find('title=', pos1, posb) + 7
                    if pos == 6:
                        pos = posa + lst
                        while '<' in page_part[pos:pos + 1]:
                            pos = page_part.find('>', pos, pos2) + 1
                        name_ = page_part[pos:page_part.find('<', pos, pos2)]
                    else:
                        name_ = page_part[pos:page_part.find('"', pos, pos2)]
                else:
                    name_ = page_part[pos1:page_part.find('<', pos1, pos2)]
                result.append({'name_rom': normal_rom(name_)})
                pos1 = page_part.find('<li>', pos1, pos2) + 4
            return result
        else:
            pos = page_part.find("title=", posa + lst, posb) + 7
            if pos > 6:
                name_rom = page_part[pos:page_part.find('"', pos, posb)]
                orig_rom(name_rom)
                continue
            pos = posa + lst
            while '<' in page_part[pos:pos + 1]:
                pos = page_part.find('>', pos, posb) + 1
            name_rom = page_part[pos:posb]
            if "<br />" in name_rom:
                names = name_rom.split("<br />")
                result.extend([{'name_rom': normal_rom(name)} for name in names])
            else:
                result.append({'name_rom': normal_rom(name_rom)})
    if not len(result):
        posa = page_part.find('>Directed by</th>') + 17
        if posa > 17:
            pose = page_part.find('</td>', posa)
            pos = page_part.find('title=', posa, pose) + 7
            if pos > 7:
                name_rom = page_part[pos:page_part.find('"', pos)]
            else:
                pos1, pos2 = _pos_ab(page_part, posa, pose)
                name_rom = page_part[pos1:pos2]
            orig_rom(name_rom)
    return result


def number_of_volumes(page_part: str) -> int:
    """
    Извлечение количества томов манги из соответствующей части инфо-блока в WP.
    :param page_part: Часть страницы манги в WP (HTML-код).
    :return: Количество томов манги в WP.
    """
    pos = page_part.find('<th scope="row" class="infobox-label">Volumes</th><td class="infobox-data">') + 75
    if pos == 74:
        return 0
    pos2 = page_part.find('</td>', pos)
    pos1 = page_part.find(' ', pos, pos2)
    if pos1 != -1:
        return int(page_part[pos:pos1])
    return int(page_part[pos:pos2])


def publications(page_part: str) -> list[dict[str, str | int]]:
    """
    Извлечение наименований издательства и издания в WP.
    :param page_part: Часть страницы манги в WP (HTML-код).
    :return: Список наименований издательства и издания в WP.
    """
    res = {'publication': []}
    for pp, tpp in {'publishing': "Published by", 'publication': "Magazine"}.items():
        st = f'<tr><th scope="row" class="infobox-label">{tpp}</th>'
        lst = len(st)
        posa = page_part.find(st) + lst
        if posa > lst - 1:
            posb = page_part.find('</td></tr>', posa)
            pos1 = page_part.find('<ul>', posa, posb) + 4
            if pos1 > 3:
                pos2 = page_part.find('</ul>', pos1, posb)
                pos1 = page_part.find('<li>', pos1, pos2) + 4
                while pos1 > 3:
                    if '<a ' in page_part[pos1:pos1 + 3]:
                        pos = page_part.find('title=', pos1, posb) + 7
                        if pos == 6:
                            pos = posa + lst
                            while '<' in page_part[pos:pos + 1]:
                                pos = page_part.find('>', pos, pos2) + 1
                            res[pp].append(page_part[pos:page_part.find('</a>', pos, pos2)])
                        else:
                            res[pp].append(page_part[pos:page_part.find('"', pos, pos2)])
                    else:
                        res[pp].append(page_part[pos1:page_part.find('</li>', pos1, pos2)])
                    pos1 = page_part.find('<li>', pos1, pos2) + 4
            else:
                pos = page_part.find('title="', posa, posb) + 7
            if pos > 6:
                tmp = page_part[pos:page_part.find('"', pos)]
            else:
                pos = page_part.find('<td class="infobox-data">', posa, posb) + 25
                if '<i>' in page_part[pos:posb]:
                    pos = pos + 3
                    posb = posb - 4
                tmp = page_part[pos:posb]
            if pp == "publishing":
                res[pp] = tmp
            elif tmp not in res[pp]:
                res[pp].append(tmp)
        elif pp == 'publication':
            res.update({pp: [f'? ({res['publishing']})'], 'type': 2})
        else:
            break
    res = [{'publication': frequency(dn.o_ou(pc)).replace("MediaWorks", "Media Works").removesuffix(" (publisher)"),
            'publishing': res['publishing'], 'type': 2 if 'type' in res and res['type'] == 2 else 1}
           for pc in res['publication']]
    return res


def extraction_manga(page_part: str, _page: str
                     ) -> dict[str, str | list[dict[str, str] | None] | int | list[str | None]]:
    """
    Извлечение данных по манге из соответствующей части инфо-блока в WP.
    :param page_part: Часть страницы манги в WP (HTML-код).
    :param _page: Страница манги в WP (HTML-код).
    :return: Словарь данных по манге в WP:
    {
        'name_eng': str,
        'author_of_manga': list[dict[str, str] | None],
        'number_of_volumes': int,
        'number_of_chapters': int,
        'date_of_premiere': str,
        'publication': list[dict[str, str | int]]
    }
    """
    print("- " * 4, "wp.extraction_manga")
    nc = number_of_chapters(page_part)
    if not nc:
        nc = number_of_chapters_2(_page)
    result = {
        'name_eng': title(page_part),
        'author_of_manga': authors(page_part, "Written", "Illustrated"),
        'number_of_volumes': number_of_volumes(page_part),
        'number_of_chapters': nc,
        'date_of_premiere': date_of_premiere(page_part),
        'publication': publications(page_part)
    }
    return result


def anime_format(page_part: str) -> str | None:
    """
    Извлечение формата anime из соответствующей части инфо-блока в WP.
    :param page_part: Часть страницы anime в WP (HTML-код).
    :return: Формата anime в WP либо None.
    """
    t = page_part[:page_part.find('</')]
    return FORM_WP[t] if t in FORM_WP else FORM_WP['Anime film series'] if 'movie' in t.lower() else None


def number_of_episodes(page_part: str) -> int:
    """
    Извлечение количества эпизодов anime из соответствующей части инфо-блока в WP.
    :param page_part: Часть страницы anime в WP (HTML-код).
    :return: Количество эпизодов anime в WP.
    """
    sa = '<tr><th scope="row" class="infobox-label">'
    sb = '</th><td class="infobox-data">'
    for st in ("Episodes", '<abbr title="Number">No.</abbr> of episodes'):
        s = f"{sa}{st}{sb}"
        pos = page_part.find(s)
        if pos > 0:
            pos += len(s)
            break
    else:
        return 1
    pos2 = page_part.find('</', pos)
    pos1 = page_part.find(' ', pos, pos2)
    if pos1 != -1:
        return int(page_part[pos:pos1])
    return int(page_part[pos:pos2])


def duration(page_part: str) -> str | None:
    """
    Извлечение продолжительности эпизода anime из соответствующей части инфо-блока в WP.
    :param page_part: Часть страницы anime в WP (HTML-код).
    :return: Продолжительность эпизода anime в WP либо None.
    """
    for th in ('>Runtime<', '>Running time<'):
        pos1 = page_part.find(th)
        if pos1 > 0:
            pos1 += len(th)
            pos1, pos2 = _pos_ab(page_part, pos1, page_part.find('</td>', pos1))
            pos = page_part.find(' ', pos1, pos2)
            if pos != -1:
                pos3 = page_part.find('–', pos1, pos) + 1
                dur = page_part[pos3:pos] if pos3 != 0 else page_part[pos1:pos]
            else:
                dur = page_part[pos1:pos2]
            return dn.hours_minutes(int(dur)) if dur.isdigit() else None


def studios(page_part: str) -> list[str] | None:
    """
    Извлечение студий anime из соответствующей части инфо-блока в WP.
    :param page_part: Часть страницы anime в WP (HTML-код).
    :return: Список студий anime в WP либо None.
    """
    pos = page_part.find('<tr><th scope="row" class="infobox-label">Studio</th><td class="infobox-data">') + 78
    if pos > 77:
        pos2 = page_part.find('</td></tr>', pos)
        pos1 = page_part.find('<ul>', pos, pos2) + 4
        res = []
        if pos1 > 3:
            pos2 = page_part.find('</ul>', pos1, pos2)
            pos1 = page_part.find('<li>', pos1, pos2) + 4
            while pos1 > 3:
                if '<a ' in page_part[pos1:pos1 + 3]:
                    pos = page_part.find('>', pos1, pos2) + 1
                    res.append(page_part[pos:page_part.find('<', pos, pos2)].strip())
                else:
                    res.append(page_part[pos1:page_part.find('<', pos1, pos2)].strip())
                pos1 = page_part.find('<li>', pos1, pos2) + 4
        else:
            for name in page_part[pos:pos2].split("<br />"):
                if '<a ' in name:
                    pos = name.find('>') + 1
                    res.append(name[pos:name.find('</a>', pos)].strip())
                else:
                    res.append(name)
        return res


def extraction_anime(page_part: str) -> dict[str, str | int | list[str] | list[dict[str, str]] | None]:
    """
    Извлечение данных по anime из соответствующей части инфо-блока в WP.
    :param page_part: Часть страницы anime в WP (HTML-код).
    :return: Словарь данных по anime в WP:
    {
        'name_eng': str,
        'format': str,
        'number_of_episodes': int,
        'duration': str,
        'date_of_premiere': str,
        'studio': list[str],
        'director': list[dict[str, str] | None]
    }
    """
    print("- " * 4, "wp.extraction_anime")
    result = {
        'name_eng': title(page_part),
        'format': anime_format(page_part),
        'number_of_episodes': number_of_episodes(page_part),
        'duration': duration(page_part),
        'date_of_premiere': date_of_premiere(page_part),
        'studio': studios(page_part),
        'director': authors(page_part, "Directed")
    }
    return result


def extraction_data(page_parts: dict[str, dict[str, dict[str, str]]], _pages: dict[str, str]
                    ) -> dict[str, dict[str, str | int | list[str | None] | list[dict[str, str] | None] | None]]:
    """
    Извлечение данных из частей инфо-блоков в WP.
    :param page_parts: Словарь частей страниц — результат filter_page_parts.
    :param _pages: Словарь HTML-страниц из WP.
    :return: Словарь словарей данных по манге и anime в WP.
    """
    print("- wp.extraction_data(page_parts, _pages)")
    res = {}
    for am, pages in page_parts.items():
        print("- - ", am)
        if am not in res:
            res[am] = {}
        for tit, page_part in pages.items():
            print("- " * 3, tit)
            res[am][tit] = (extraction_anime(page_part['page_part']) if am == A else
                            extraction_manga(page_part['page_part'], _pages[page_part['page_title']]))
    return res
