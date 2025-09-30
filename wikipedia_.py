"""
Поиск страниц в Wikipedia (en) (далее — WP) и их обработка.
"""
from time import sleep
import requests
import wikipedia
import dateutil.parser as date_parser

from decode_name import normal_name, month, title_index, hours_minutes
from constants import *
from config import FORM_WP, frequency


def page(url: str) -> str:
    """
    Получение HTML-кода страницы по внутренней ссылке в WP. Используется requests.
    :param url: Внутренняя ссылка (после /wiki/).
    :return: HTML-код страницы или строка статус-кода, если он не равен 200.
    """
    sleep(1)
    result = requests.get(WPE + url)
    if result.status_code == 200:
        return result.text
    return str(result.status_code)


def html(search: str) -> str:
    """
    Получение страницы (HTML-кода) из WP. Используется wikipedia.
    Если в течение 15 секунд нет результата, происходит переключение на page, а пробелы в search заменяются на «_».
    :param search: Искомое наименование.
    :return: Страница (HTML-код).
    """
    b = 0
    while True:
        sleep(1)
        try:
            result = wikipedia.page(search).html()
        except wikipedia.WikipediaException:
            b += 1
            if b == 15:
                return page(search.replace(' ', '_'))
            continue
        return result


def search_pages(search: str) -> dict[str, str]:
    """
    Поиск страниц по наименованию в WP.
    :param search: Искомое наименование.
    :return: Словарь {title_norm: HTML} страниц в WP.
    """
    search_ = normal_name(search)
    _page = html(search_)
    if (('<div class="shortdescription nomobile noexcerpt noprint searchaux" style="display:none">'
         'Name list</div>') in _page or _page == '404' or (M not in search_ and search_ not in normal_name(_page)) or
            (M in search_ and search_[:-6] not in normal_name(_page))):
        return {}
    res = {search_: _page}
    posb = _page.find('<table') + 7
    if _page.find('class="box-Lead_too_short', posb) != -1:
        posb = _page.find('<table', posb) + 7
    pose = _page.find('</table>', posb)
    pos = _page.find('class="infobox-full-data"', posb, pose)
    if pos != -1:
        pos1 = _page.find('class="infobox-subheader"', posb, pose) + 25
        while pos1 > 24 and pos > 0:
            pos2 = _page.find('class="infobox-subheader"', pos1, pose)
            if pos2 == -1:
                pos2 = pose
            if pos2 > pos:
                pos = _page.find('>', pos1, pos) + 1
                if pos == 0:
                    break
                t = _page[pos:_page.find('<', pos, pos2)]
                if 'Anime' in t or 'Manga' in t:
                    posu = _page.find('<ul>', pos, pos2) + 4
                    if posu != 3:
                        posl = _page.find('</ul>', posu, pos2)
                        posi = _page.find('<i>', posu, posl) + 3
                        if posi != 2:
                            post = posu
                            while True:
                                post = _page.find('title="', post, posl) + 7
                                if post == 6:
                                    break
                                ttl = _page[post:_page.find('"', post, posl)]
                                res.update(search_pages(ttl))
            pos1 = pos2 + 25
            pos = _page.find('class="infobox-full-data"', pos1, pose)
    return res


def manga_anime_in_page(pages: dict[str, str]) -> dict[str, dict[str, dict[str, str]]]:
    """
    Извлечение из страницы частей страницы (частей инфоблоков) по отдельным манге и anime в WP.
    :param pages: Страница (HTML-код) в WP.
    :return: Словарь:
    {
        page_title_norm: {
            'manga': {
                manga_title_norm: page_part,

                ...
            },

            'anime': {
                anime_title_norm: page_part,

                ...
            }
        }
    }
    """
    result = {}
    for page_title_norm, page in pages.items():
        res = {}
        posb = page.find('<table') + 7
        if (page.find('class="box-Lead_too_short', posb) != -1 or
                page.find('>This article <b>needs additional citations for', posb) != -1):
            posb = page.find('<table', posb) + 7
        pose = page.find('</table>', posb)
        pos1 = page.find('class="infobox-subheader"', posb, pose)
        if pos1 != -1:
            l1 = 25
            v2 = False
        else:
            pos1 = page.find('class="infobox-above summary"', posb, pose)
            l1 = 29
            v2 = True
        while pos1 > l1 - 1:
            pos2 = page.find('class="infobox-subheader"', pos1 + l1, pose)
            if pos2 == -1:
                pos2 = pose
            if 'class="infobox-full-data"' not in page[pos1:pos2]:
                pos = page.find('>', pos1, pos2) + 1
                if pos == 0:
                    break
                posa = page.find('<', pos, pos2)
                if posa == pos:
                    pos = page.find('>', pos, pos2) + 1
                    posa = page.find('<', pos, pos2)
                t = page[pos:posa]
                if 'Manga' in t or 'anim' in t.lower():
                    posa = page.find('<tr><th colspan="2" class="infobox-header" style="background:#EEF; '
                                     'font-weight:normal;"><i>', pos1, pos2) + 91
                    if posa != 90:
                        posb = page.find('<', posa, pos2)
                        ttl = normal_name(page[posa:posb])
                    else:
                        ttl = page_title_norm.removesuffix(" manga")
                    am = M if 'Manga' in t else A
                    if am not in res:
                        res[am] = {}
                    if ttl in res[am]:
                        ttl += f' ({t})'
                    res[am][ttl] = page[pos:pos2]
                elif v2:
                    page_part = page[pos:pos2]
                    am = A if '>Directed by</th>' in page_part else M
                    if am not in res:
                        res[am] = {}
                    res[am][t] = page_part
                    break
            pos1 = pos2
        result[page_title_norm] = res
    return result


def date_of_premiere(page_part: str) -> str | None:
    """
    Извлечение даты премьеры из части страницы в WP.
    :param page_part: Часть страницы (HTML-код) в WP.
    :return: Дата премьеры в WP либо None.
    """
    posa = page_part.find('<th scope="row" class="infobox-label">Released</th><td class="infobox-data">') + 76
    posb = page_part.find('<th scope="row" class="infobox-label">Original run</th><td class="infobox-data">') + 80
    posc = page_part.find('<th scope="row" class="infobox-label">Published</th><td class="infobox-data">') + 77
    posd = page_part.find('>Release date</div></th>') + 24
    posf = page_part.find('<th scope="row" class="infobox-label">Release</th><td class="infobox-data">') + 75
    v2 = False
    if posa == 75 and posb != 79:
        pos1 = posb
    elif posb == 79 and posa != 75:
        pos1 = posa
    elif posa == 75 and posb == 79 and posc != 76:
        pos1 = posc
    elif posd != 23:
        pos1 = page_part.find('<', posd)
        v2 = True
        pos2 = posd
    elif posf != 74:
        pos1 = posf
    else:
        return
    pose = page_part.find('</td>', pos1)
    pos = page_part.find('<', pos1, pose)
    while pos == pos1 or pos == pos1 + 1:
        pos1 = page_part.find('>', pos1, pose) + 1
        pos = page_part.find('<', pos1, pose)
    if not v2:
        posa = page_part.find('</span>', pos1, pose)
        posb = page_part.find('<span', pos1, pose)
        pos2 = min(posa, posb)
        if pos2 < 0:
            pos2 = page_part.find('<', pos1, pose)
        if pos2 < 0:
            pos2 = pose
    date = page_part[pos1:pos2].replace('&#160;', ' ').strip()
    if len(date) == 4:
        return date_parser.parse(date).strftime('%Y') + '-12-31'
    date_ = date.split(' ')
    if len(date_) == 2 and ((date_[0].isdigit() and len(date_[0]) == 4) or (date_[1].isdigit() and len(date_[1]) == 4)):
        return month(date)
    elif len(date_) == 2:
        pos2 = page_part.find('</span>', pos1, pose)
        if pos2 != -1 and 'start' in page_part[pos1:pos2]:
            while pos < pos2:
                pos1 = page_part.find('>', pos1, pose) + 1
                pos = page_part.find('<', pos1, pose)
            return page_part[pos1:pos2].strip()
    return date_parser.parse(date).strftime('%Y-%m-%d')


def filter_page_parts(pages: dict[str, dict[str, dict[str, str]]]) -> dict[str, dict[str, str]]:
    """
    Фильтр частей страниц, удаляющий повторы, и переформатирование словаря частей страниц.
    :param pages: Словарь частей страниц — результат manga_anime_in_page.
    :return: Словарь
    {
        'manga': {
            title_norm: page_part,

            ...
        },

        'anime': {
            title_norm: page_part,

            ...
        }
    }
    """
    res = {}
    for _page in pages.values():
        for am, page_parts in _page.items():
            if am not in res:
                res[am] = {}
            for ttl, page_part in page_parts.items():
                fpp = True
                for pp in res[am].values():
                    if pp == page_part:
                        fpp = False
                        break
                if fpp:
                    if am == A:
                        ttl = ttl.replace(' (Original video animation)', ' (OVA)')
                    ttl += f' ({date_of_premiere(page_part)})'
                    res[am][title_index(res[am], ttl)] = page_part
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
    Извлечение количества глав манги из соответствующей части инфоблока в WP.
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
    pos = _page.find('<table', pos)
    posf = _page.find('</table>', pos)
    return _count_li(_page, pos, posf)


def title(page_part: str) -> str:
    """
    Извлечение наименования (англ.) из соответствующей части инфоблока в WP.
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
    Извлечение имён авторов манги или режиссёров anime из соответствующей части инфоблока в WP.
    :param page_part: Часть страницы манги в WP (HTML-код).
    :param args: Кортеж категорий авторов ("Written", "Illustrated", "Directed").
    :return: Список словарей имён авторов манги или режиссёров anime в WP.
    """
    def orig_rom() -> tuple[str, str]:
        """
        Извлечение оригинального и ромадзи имён из HTML-страницы автора в WP.
        :return: Кортеж оригинального и ромадзи имён автора в WP.
        """
        def normal_rom(_name: str) -> str:
            _name = _name.split()
            return normal_name(_name[1].lower()).title() + " " + normal_name(_name[0].lower()).title()

        pos = apage.find('<tr><th colspan="2" class="infobox-above" style="font-size:125%;">'
                         '<div style="display:inline;" class="fn">') + 106
        name_rom = ""
        if pos > 105:
            name_rom = normal_rom(apage[pos:apage.find("<", pos)])
        else:
            pos = apage.find('<tr><th colspan="2" class="infobox-above" style="font-size:125%;">'
                             '<div class="fn">') + 82
            if pos == 81:
                pos = apage.find('<tr><th colspan="2" class="infobox-above fn">') + 45
            if pos > 44:
                name_rom = normal_rom(apage[pos:apage.find("</div", pos)])
        name_orig = ""
        if (pos := apage.find('<tr><td colspan="2" class="infobox-subheader" style="font-size:125%;">'
                              '<div class="nickname" lang="ja">') + 102) > 101:
            name_orig = apage[pos:apage.find("</div", pos)]
        elif (pos := apage.find('<span lang="ja">') + 16) > 15:
            pos2 = apage.find("</span>", pos)
            pos1 = apage.find(" (", pos, pos2)
            name_orig = apage[pos:pos1] if pos1 != -1 else apage[pos:pos2]
            while '<' in name_orig:
                pos = name_orig.find('<')
                pos2 = name_orig.find('>', pos) + 1
                name_orig = name_orig[:pos] + name_orig[pos2:]
            if not name_rom:
                pos = apage.find('<i lang="ja-Latn">', pos) + 18
                name_rom = apage[pos:apage.find('</i>', pos)]
        return name_orig, name_rom

    result = []
    for staff in args:
        pos, posa, posb = 0, 0, 0
        st = f'<tr><th scope="row" class="infobox-label">{staff}&#160;by</th><td class="infobox-data">'
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
                        name_ = page_part[pos:page_part.find('</a>', pos, pos2)].split()
                    else:
                        name_ = page_part[pos:page_part.find('"', pos, pos2)].split()
                else:
                    name_ = page_part[pos1:page_part.find('</li>', pos1, pos2)].split()
                result.append({'name_rom': name_[1] + " " + name_[0]})
                pos1 = page_part.find('<li>', pos1, pos2) + 4
            return result
        else:
            pos = page_part.find("title=", posa + lst, posb) + 7
            if pos == 6:
                pos = posa + lst
                while '<' in page_part[pos:pos + 1]:
                    pos = page_part.find('>', pos, posb) + 1
                name_ = page_part[pos:posb].split()
                name_rom = name_[1] + " " + name_[0]
                result.append({'name_rom': name_rom})
                continue
            apage = html(page_part[pos:page_part.find('"', pos, posb)])
            name_orig, name_rom = orig_rom()
            result.append({'name_orig': name_orig, 'name_rom': name_rom})
    if not len(result):
        pos = page_part.find('>Directed by</th>') + 17
        pos = page_part.find('title=', pos) + 7
        apage = html(page_part[pos:page_part.find('"', pos)])
        name_orig, name_rom = orig_rom()
        result.append({'name_orig': name_orig, 'name_rom': name_rom})
    return result


def number_of_volumes(page_part: str) -> int:
    """
    Извлечение количества томов манги из соответствующей части инфоблока в WP.
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
    for pp, tpp in {'publishing': "Published&#160;by", 'publication': "Magazine"}.items():
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
                if pp == "publishing":
                    res[pp] = page_part[pos:page_part.find('"', pos)]
            else:
                pos = page_part.find('<td class="infobox-data">', posa, posb) + 25
                if '<i>' in page_part[pos:posb]:
                    pos = pos + 3
                    posb = posb - 4
                res[pp].append(page_part[pos:posb])
            if pp == 'publication':
                res[pp] = [frequency(tmp).replace("MediaWorks", "Media Works").removesuffix(" (publisher)")
                           for tmp in res[pp]]
        elif pp == 'publication':
            res.update({pp: [f'? ({res['publishing']})'], 'type': 2})
        else:
            break
    res = [{'publication': pc, 'publishing': res['publishing'], 'type': 2 if 'type' in res and res['type'] == 2 else 1}
           for pc in res['publication']]
    return res


def extraction_manga(page_part: str, _page: str
                     ) -> dict[str, str | list[dict[str, str] | None] | int | list[str | None]]:
    """
    Извлечение данных по манге из соответствующей части инфоблока в WP.
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
    Извлечение формата anime из соответствующей части инфоблока в WP.
    :param page_part: Часть страницы anime в WP (HTML-код).
    :return: Формата anime в WP либо None.
    """
    t = page_part[:page_part.find('</')]
    return FORM_WP[t] if t in FORM_WP else None


def number_of_episodes(page_part: str) -> int:
    """
    Извлечение количества эпизодов anime из соответствующей части инфоблока в WP.
    :param page_part: Часть страницы anime в WP (HTML-код).
    :return: Количество эпизодов anime в WP.
    """
    pos = page_part.find('<tr><th scope="row" class="infobox-label">Episodes</th><td class="infobox-data">') + 80
    if pos > 79:
        pos2 = page_part.find('</', pos)
        pos1 = page_part.find(' ', pos, pos2)
        if pos1 != -1:
            return int(page_part[pos:pos1])
        return int(page_part[pos:pos2])


def duration(page_part: str) -> str | None:
    """
    Извлечение продолжительности эпизода anime из соответствующей части инфоблока в WP.
    :param page_part: Часть страницы anime в WP (HTML-код).
    :return: Продолжительность эпизода anime в WP либо None.
    """
    pos = page_part.find('<tr><th scope="row" class="infobox-label">Runtime</th><td class="infobox-data">') + 79
    if pos > 78:
        pos2 = page_part.find(' ', pos, page_part.find('</td>', pos))
        if pos2 != -1:
            pos1 = page_part.find('–', pos, pos2) + 1
            dur = page_part[pos1:pos2] if pos1 != 0 else page_part[pos:pos2]
            return hours_minutes(int(dur)) if dur.isdigit() else None


def studios(page_part: str) -> list[str] | None:
    """
    Извлечение студий anime из соответствующей части инфоблока в WP.
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
                    res.append(page_part[pos:page_part.find('</a>', pos, pos2)])
                else:
                    res.append(page_part[pos1:page_part.find('</li>', pos1, pos2)])
                pos1 = page_part.find('<li>', pos1, pos2) + 4
            return res
        else:
            if '<a ' in page_part[pos:pos + 3]:
                pos = page_part.find('>', pos, pos2) + 1
                while pos > 0:
                    res.append(page_part[pos:page_part.find('</a>', pos, pos2)])
                    pos = page_part.find('<a ', pos, pos2)
                    pos = page_part.find('>', pos, pos2) + 1
                return res
            res = [page_part[pos:pos2]]
            return res


def extraction_anime(page_part: str) -> dict[str, str | int | list[str] | list[dict[str, str]] | None]:
    """
    Извлечение данных по anime из соответствующей части инфоблока в WP.
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


def extraction_data(page_parts: dict[str, dict[str, str]], _pages: dict[str, str]
                    ) -> dict[str, dict[str, str | int | list[str | None] | list[dict[str, str] | None] | None]]:
    """
    Извлечение данных из частей инфоблоков в WP.
    :param page_parts: Словарь частей страниц — результат manga_anime_in_page.
    :param _pages: Словарь HTML-страниц из WP.
    :return: Словарь словарей данных по манге и anime в WP.
    """
    res = {}
    for am, pages in page_parts.items():
        if am not in res:
            res[am] = {}
        for tit, page_part in pages.items():
            res[am][tit] = (extraction_anime(page_part) if am == A else
                            extraction_manga(page_part, _pages[tit[:tit.find(" (")]]))
    return res
