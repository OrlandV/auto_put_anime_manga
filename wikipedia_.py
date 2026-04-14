"""
Поиск страниц в Wikipedia (en) (далее — WP) и их обработка.
"""
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
import dateutil.parser as date_parser

from constants import *
from file_cache import anti_bot
from config import FORM_WP, frequency
import decode_name as dn


def page(url: str) -> BeautifulSoup | None:
    """
    Получение HTML-кода страницы по внутренней ссылке в WP. Используется пакет requests.
    :param url: Внутренняя ссылка (после /wiki/).
    :return: HTML-код страницы или None, если статус-код не входит в интервал [200, 400).
    """
    res = BeautifulSoup(anti_bot("WP", WPES + url), "html.parser")
    return res if len(res) else None


class Page:
    """
    Страница из Wikipedia (en).

    Свойства:
    html — HTML-код страницы (или None, если статус-код не входит в интервал [200, 400));
    url — внутренняя ссылка (после /wiki/).
    """
    def __init__(self, search: str):
        """
        Получение страницы (HTML-кода) из WP.
        Если искомое наименование не найдено, происходит переключение на page, а пробелы в search заменяются на «_».
        :param search: Искомое наименование.
        """
        self.url = None
        _html = BeautifulSoup(anti_bot("WP", WPE_SEARCH + search.replace(" ", "+")), "html.parser")
        ul = _html.find("ul", {'class': "mw-search-results"}).contents
        for li in ul:
            div = li.find_next("div", {'class': "mw-search-result-heading"})
            if search in div.a.text:
                self.url = div.a.attrs['href'].removeprefix("/wiki/")
            elif search in dn.normal_name(li.find_next("div", {'class': "searchresult"}).text):
                self.url = li.a.attrs['href'].removeprefix("/wiki/")
            if self.url:
                self.html = page(self.url)
                break
        else:
            url = search.replace(" ", "_")
            self.html = page(url)
            self.url = url
        if f"{A} and {M}" not in self.html.text.lower():
            self.html = None
            self.url = None


def search_pages(search: str, res: dict[str, BeautifulSoup] = {}) -> dict[str, BeautifulSoup]:
    """
    Поиск страниц по наименованию в WP.
    :param search: Искомое наименование.
    :param res: Дополняемый словарь {title: HTML} страниц в WP.
    :return: Итоговый словарь {title: HTML} страниц в WP.
    """
    def res_update(tag: Tag) -> None:
        nonlocal res
        for li in tag.find_all("li"):
            if "drama" in li.a.text:
                continue
            a_title = li.a.attrs['title']
            if a_title not in res:
                res = search_pages(a_title, res)

    def res_update_ul() -> None:
        ifd = subheader.parent.next_sibling.td
        if ifd.get("class") == ["infobox-full-data"]:
            ul = ifd.find("ul")
            if ul and not ul.find("div"):
                res_update(ul)

    print(f"wp.search_pages('{search}')")
    _page = Page(search)
    if _page.html:
        if _page.html.find(lambda tag: tag.name == "div" and tag.get('class') == ["shortdescription"]
                                       and tag.get("style") == ["display:none"]):
            return res
        res[_page.url.replace("_", " ")] = _page.html
        for link in (_page.html.find("table", {'class': "infobox"})
                .find_all("link", {'href': "mw-data:TemplateStyles:r1316064257"})):
            if subheader := link.find("td", {'class': "infobox-subheader"}):
                sht = subheader.text
                if "anim" in sht.lower() or "Manga" in sht:
                    res_update_ul()
                elif sht in ("Feature films", "Films", "Related media", "Related series", "Related works", "Spin-offs",
                             "Television series"):
                    if ol := link.find("ol"):
                        res_update(ol)
                    else:
                        res_update_ul()
    return res


def manga_anime_in_page(pages: dict[str, BeautifulSoup | str]
                        ) -> dict[str, dict[str, dict[str, dict[str, BeautifulSoup | dict[str, str]]]]]:
    """
    Извлечение из страницы частей страницы (частей инфо-блоков) по отдельным манге и anime в WP.
    :param pages: Словарь страниц (HTML-код) в WP.
    :return: Словарь:
    {
        page_title: {
            'manga': {
                manga_title: {
                    'page_part': page_part,

                    'titles': {
                        'eng': title_eng,

                        'orig': title_orig,

                        'rom': title_rom

                    },

                ...
            },

            'anime': {
                anime_title: {
                    'page_part': page_part,

                    'titles': {
                        'eng': title_eng,

                        'orig': title_orig,

                        'rom': title_rom

                    },

                ...
            }
        }
    }
    """
    def res_add() -> None:
        nonlocal res, res_, ttl
        if am not in res:
            res[am] = {}
        ttl = ttl or ttl_['rom'] or ttl_['eng'] or ttl_['orig']
        if ttl in res[am]:
            t1 = f"{ttl} ({res[am][ttl].td.text})"
            res[am][t1] = res[am][ttl]
            del res[am][ttl]
            ttl += f" ({t})"
        res[am][ttl] = {'page_part': res_}
        if ttl_['rom'] or ttl_['eng'] or ttl_['orig']:
            res[am][ttl]['titles'] = ttl_
        res_ = BeautifulSoup("<table></table>", "html.parser")
        ttl = None

    print("wp.manga_anime_in_page(pages):")
    result = {}
    pages = pages.items() if isinstance(pages, dict) else pages
    for page_title, _page in pages:
        print("-", page_title)
        s = ns = n = e = ias = ttl = None
        if isinstance(_page, str):
            _page = BeautifulSoup(_page, "html.parser")
        tr = _page.find("table", {'class': "infobox"}).tbody.contents
        i = 0
        res_ = BeautifulSoup("<table></table>", "html.parser")
        res = {}
        ttl_ = {'eng': None, 'orig': None, 'rom': None}
        while i < len(tr):
            if s and isinstance(tr[i], NavigableString):
                s = False
                i += 1
                continue
            elif (not s and not isinstance(tr[i], NavigableString)
                  and (tr[i].th or (tr[i].td and tr[i].td.attrs['class'] != ["infobox-full-data"]
                       and (len(tr) > i + 1 and tr[i + 1].th
                            or (tr[i + 1].td and tr[i + 1].td.attrs['class'] != ["infobox-full-data"]))))):
                if tr[i].td and tr[i].td.has_attr("class") and tr[i].td.attrs['class'] == ["infobox-subheader"]:
                    t = tr[i].td.text
                    if "Manga" in t or "anim" in t.lower():
                        if n:
                            am = M if "Manga" in t else A
                            n = False
                        elif not n and ns is None:
                            n = True
                        else:
                            am = M if "Manga" in t else A
                    elif t in ("Feature films", "Films", "Live-action film", "Related series", "Related works",
                               "Spin-offs", "Television series"):
                        s = True
                        i += 1
                        continue
                    else:
                        ttl_['eng'] = t
                elif (tr[i].th and tr[i].th.has_attr("class")
                      and tr[i].th.attrs['class'] == ["infobox-above", "summary"]):
                    ias = True
                    ttl = tr[i].th.text
                elif ias and tr[i].th and tr[i].th.string == "Directed by":
                    am = A
                elif (tr[i].th and tr[i].th.has_attr("class") and tr[i].th.attrs['class'] == ["infobox-header"]
                      and not ias):
                    if tr[i].th.span:
                        if sp := tr[i].th.find(
                            lambda tag: tag.name == "span" and tag.has_attr("title")
                                        and tag.attrs['title'] == "Japanese-language text"
                        ):
                            ttl_['orig'] = sp.text
                        if sp := tr[i].th.find(
                            lambda tag: tag.name == "span" and tag.has_attr("title")
                                        and tag.attrs['title'] == "Japanese-language romanization"
                        ):
                            ttl_['rom'] = sp.text
                    else:
                        ttl = tr[i].th.text
                if not e and not n:
                    res_.table.append(tr[i])
            elif isinstance(tr[i], NavigableString) and not ns:
                ns = True
                i += 1
            elif isinstance(tr[i], NavigableString) and len(res_.table.contents):
                res_add()
                if e:
                    break
                am = M
            else:
                i += 1
            if n:
                res_add()
                ias = ttl = False
            if not tr or (len(tr) == i and len(res_.table.contents)):
                res_add()
                break
        result[page_title] = res
    return result


def filter_page_parts(pages: dict[str, dict[str, dict[str, dict[str, BeautifulSoup | dict[str, str]]]]]
                      ) -> dict[str, dict[str, dict[str, BeautifulSoup | dict[str, str]]]]:
    """
    Фильтр частей страниц, удаляющий повторы, и переформатирование словаря частей страниц.
    :param pages: Словарь частей страниц — результат manga_anime_in_page.
    :return: Словарь
    {
        'manga': {
            title: page_part,

            ...
        },

        'anime': {
            title: page_part,

            ...
        }
    }
    """
    print("wp.filter_page_parts(pages):")
    res = {}
    for page_title, _page in pages.items():
        print("-", page_title)
        for am, page_parts in _page.items():
            print("- " * 2, am)
            if am not in res:
                res[am] = {}
            for ttl, page_part in page_parts.items():
                print("- " * 3, ttl)
                fpp = True
                for pp in res[am].values():
                    if pp == page_part:
                        fpp = False
                        break
                if fpp:
                    if am == A:
                        ttl = (ttl.replace(' (Original video animation)', ' (OVA)')
                               .replace(' (Anime television series)', ' (TV)'))
                    res[am][dn.title_index(res[am], ttl)] = page_part
    return res


def title_orig(part: dict[str, BeautifulSoup | dict[str, str]]) -> str | None:
    """
    Извлечение оригинального наименования манги или anime из соответствующей части инфо-блока в WP.
    :param part: Часть страницы манги в WP (HTML-код).
    :return: Оригинальное наименование манги или anime в WP, если найдено. Иначе — None.
    """
    if "titles" in part and "orig" in part['titles']:
        return part['titles']['orig']
    th = part['page_part'].find(lambda tag: tag.name == "th" and tag.attrs['class'] == ["infobox-label"]
                                            and tag.text == "Kanji")
    if th:
        return dn.decode_name(th.next_sibling.text)


def authors(part: BeautifulSoup, *args) -> list[dict[str, str] | None]:
    """
    Извлечение имён авторов манги или режиссёров anime из соответствующей части инфо-блока в WP.
    :param part: Часть страницы манги в WP (HTML-код).
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
        _name = _name.removeprefix("/wiki/")
        apage = page(_name)
        if apage:
            if (_th := apage.find("th", {'class': "infobox-above"})) is not None:
                _name = _th.text
                _name_rom = normal_rom(_name)
            elif (caption := apage.find("caption", {'class': "infobox-title"})) is not None:
                _name_rom = normal_rom(caption.text)
            div = apage.find(
                lambda tag: tag.parent.name == "td" and tag.parent.has_attr("class")
                            and tag.parent.attrs['class'] == ["infobox-subheader"] and tag.name == "div"
                            and tag.has_attr("class") and tag.attrs['class'] == ["nickname"] and tag.has_attr("lang")
                            and tag.attrs['lang'] == "ja")
            if div:
                _name_orig = div.text
            elif ((b := apage.find(lambda tag: tag.name == "b" and _name in tag.text)) is not None
                  and (span := b.find_next("span", {'lang': "ja"})) is not None):
                _name_orig = span.text
            elif (span := apage.find(
                lambda tag: tag.name == "span" and tag.has_attr("lang") and tag.attrs['lang'] == "ja"
                            and tag.parent.parent.parent.has_attr("class")
                            and "infobox-above" in tag.parent.parent.parent.attrs['class']
            )) is not None:
                span = span.text
                b = span.find(" (")
                _name_orig = span[:b] if b != -1 else span
            else:
                # _page = str(apage)
                # _pos1 = _page.find("</b> (") + 6
                # _pos2 = _page.find(" <", _pos1)
                # _name_orig = _page[_pos1:_pos2]
                # _pos1 = _pos2 + 4
                # _pos2 = _page.find("<", _pos1)
                # _name_rom = normal_rom(_page[_pos1:_pos2])
                _name_orig = _name_rom
            result.append({'name_orig': _name_orig, 'name_rom': _name_rom})
        else:
            pos = _name.find("_(")
            result.append({'name_rom': normal_rom(_name[:pos if pos > 0 else None].replace("_", " "))})

    result = []
    for staff in args:
        th = part.find(lambda tag: tag.name == "th" and tag.attrs['class'] == ["infobox-label"]
                                   and staff in tag.text)
        if th:
            td = th.next_sibling
            if td and td.ul:
                for li in td.ul.contants:
                    if li.a and li.a.has_attr("href"):
                        orig_rom(li.a.attrs['href'])
                    else:
                        result.append({'name_rom': normal_rom(li.text)})
            elif td and td.a and td.a.has_attr("href"):
                orig_rom(td.a.attrs['href'])
            else:
                result.append({'name_rom': normal_rom(td.text)})
    return result


def number_of_volumes(part: BeautifulSoup) -> int:
    """
    Извлечение количества томов манги из соответствующей части инфо-блока в WP.
    :param part: Часть страницы манги в WP (HTML-код).
    :return: Количество томов манги в WP.
    """
    td = dn.decode_name(part.find(lambda tag: tag.name == "th" and tag.attrs['class'] == ["infobox-label"]
                                              and tag.string == "Volumes").next_sibling.text)
    pos1 = td.find(" ")
    pos2 = td.find("[")
    if pos1 > 0 and pos2 > 0:
        pos = min(pos1, pos2)
    elif pos1 > 0:
        pos = pos1
    elif pos2 > 0:
        pos = pos2
    else:
        pos = 0
    return int(td[:pos] if pos > 0 else td)


def number_of_chapters(part: BeautifulSoup) -> int:
    """
    Извлечение количества глав манги из соответствующей части инфо-блока в WP.
    :param part: Часть страницы манги в WP (HTML-код).
    :return: Количество глав манги в WP. 0 — нет данных.
    """
    h = None
    if (td := part.find(lambda tag: tag.name == "th" and tag.attrs['class'] == ["infobox-label"]
                                    and tag.string == "Volumes").next_sibling) is not None:
        a = td.a
        while a and "List" not in a.text:
            a = a.find_next("a")
        if a and a.has_attr("href"):
            vol_page = page(a.attrs['href'].removeprefix("/wiki/"))
            h = vol_page.find(lambda tag: tag.name == "h2" and tag.has_attr("id")
                                          and tag.attrs['id'] in ("Volumes", "Volume_list", "Volumes_list"))
    if not h:
        h = part.find(lambda tag: tag.name == "h4" and tag.has_attr("id") and tag.attrs['id'] == "Chapter_list")
    if not h:
        return 0
    table = h.parent.find_next_sibling("table")
    return len(table.find_all("li"))


def date_of_premiere(part: BeautifulSoup) -> str | None:
    """
    Извлечение даты премьеры из части страницы в WP.
    :param part: Часть страницы (HTML-код) в WP.
    :return: Дата премьеры в WP либо None.
    """
    for t in ("Released", "Original run", "Published", "Release", "Release date", "Release dates"):
        th = part.find(lambda tag: tag.name == "th" and tag.attrs['class'] == ["infobox-label"] and tag.text == t)
        if th:
            break
    else:
        return
    td = th.next_sibling
    span = td.span
    date = dn.decode_name((span if span and span.has_attr("class") and span.attrs['class'] == ["nowrap"] else td
                           ).text.strip())
    if "(" in date:
        return date[date.find("(") + 1:date.find(")")]
    if len(date) == 4:
        return date_parser.parse(date).strftime('%Y') + '-12-31'
    date_ = date.split(' ')
    if len(date_) == 2 and ((date_[0].isdigit() and len(date_[0]) == 4) or (date_[1].isdigit() and len(date_[1]) == 4)):
        return dn.month(date)
    elif len(date_) == 2 and span:
        return span.text
    return date_parser.parse(date).strftime('%Y-%m-%d')


def publication(part: BeautifulSoup) -> list[dict[str, str | int]]:
    """
    Извлечение наименований издательства и издания в WP.
    :param part: Часть страницы манги в WP (HTML-код).
    :return: Список наименований издательства и издания в WP.
    """
    res = {'publication': []}
    for pp, tpp in {'publishing': "Published by", 'publication': "Magazine"}.items():
        th = part.find(lambda tag: tag.name == "th" and tag.attrs['class'] == ["infobox-label"]
                                   and dn.decode_name(tag.text) == tpp)
        if th:
            td = th.next_sibling
            ul = td.ul
            if ul:
                for li in ul.contents:
                    res[pp].append(li.text)
            else:
                t = td.text
                if pp == "publishing":
                    res[pp] = t
                else:
                    for ti in t.split(", "):
                        if ti not in res[pp]:
                            res[pp].append(ti)
        elif pp == 'publication':
            res.update({pp: [f'? ({res['publishing']})'], 'type': 2})
        else:
            break
    res = [{'publication': (frequency(dn.o_ou(dn.decode_name(pc))).replace("MediaWorks", "Media Works").
                            removesuffix(" (publisher)")),
            'publishing': dn.decode_name(res['publishing']), 'type': 2 if 'type' in res and res['type'] == 2 else 1}
           for pc in res['publication']]
    return res


def poster(part: BeautifulSoup) -> str | None:
    """
    Извлечение ссылки на постер из соответствующей части инфо-блока в WP.
    :param part: Часть страницы манги в WP (HTML-код).
    :return: Ссылка на постер в WP, если найдена. Иначе — None.
    """
    td = part.find("td", {'class': "infobox-image"})
    if td:
        url = "https:" + td.img.attrs['src'].replace("/thumb", "")
        p = max(url.find(".jpg/"), url.find(".png/")) + 4
        return url[:p] if p > 3 else url


def extraction_manga(part: dict[str, BeautifulSoup | dict[str, str]], tit: str
                     ) -> dict[str, str | list[dict[str, str] | None] | int | list[str | None]]:
    """
    Извлечение данных по манге из соответствующей части инфо-блока в WP.
    :param part: Часть страницы манги в WP (HTML-код).
    :param tit: Заголовок страницы.
    :return: Словарь данных по манге в WP:
    {
        'name_orig': str | None,
        'name_rom': str | None,
        'name_eng': str,
        'author_of_manga': list[dict[str, str] | None],
        'number_of_volumes': int,
        'number_of_chapters': int,
        'date_of_premiere': str | None,
        'publication': list[dict[str, str | int]],
        'poster': str | None
    }
    """
    print("- " * 3, "wp.extraction_manga")
    result = {
        'name_orig': title_orig(part),
        'name_rom': part['titles']['rom'] if "titles" in part and "rom" in part['titles'] else None,
        'name_eng': part['titles']['eng'] if "titles" in part and "eng" in part['titles'] else tit,
        'author_of_manga': authors(part['page_part'], "Written", "Illustrated"),
        'number_of_volumes': number_of_volumes(part['page_part']),
        'number_of_chapters': number_of_chapters(part['page_part']),
        'date_of_premiere': date_of_premiere(part['page_part']),
        'publication': publication(part['page_part']),
        'poster': poster(part['page_part'])
    }
    return result


def anime_format(part: BeautifulSoup) -> str | None:
    """
    Извлечение формата anime из соответствующей части инфо-блока в WP.
    :param part: Часть страницы anime в WP (HTML-код).
    :return: Формата anime в WP либо None.
    """
    def _res(t: str) -> str | None:
        return FORM_WP[t] if t in FORM_WP else FORM_WP['Anime film series'] if 'movie' in t.lower() else None

    t = part.tr.text
    res = _res(t)
    if res:
        return res
    tds = part.find_all(lambda tag: tag.name == "td" and tag.has_attr("class")
                                    and tag.attrs['class'] == ["infobox-subheader"])
    if len(tds):
        for td in tds:
            res = _res(td.text)
            if res:
                return res
    if (td := part.find("td", {'class': "infobox-image"})) is not None and "movie" in td.a.attrs['href']:
        return FORM_WP['Anime film series']


def number_of_episodes(part: BeautifulSoup) -> int:
    """
    Извлечение количества эпизодов anime из соответствующей части инфо-блока в WP.
    :param part: Часть страницы anime в WP (HTML-код).
    :return: Количество эпизодов anime в WP.
    """
    for t in ("Episodes", "No. of episodes"):
        th = part.find(lambda tag: tag.name == "th" and tag.has_attr("class")
                                   and tag.attrs['class'] == ["infobox-label"] and dn.decode_name(tag.text) == t)
        if th:
            break
    else:
        return 1
    res = dn.decode_name(th.next_sibling.text)
    for p in (" ", ","):
        if p in res:
            res = res[:res.find(p)]
    return int(res)


def duration(part: BeautifulSoup) -> str | None:
    """
    Извлечение продолжительности эпизода anime из соответствующей части инфо-блока в WP.
    :param part: Часть страницы anime в WP (HTML-код).
    :return: Продолжительность эпизода anime в WP либо None.
    """
    for t in ("Runtime", "Running time"):
        th = part.find(lambda tag: tag.name == "th" and tag.has_attr("class")
                                   and tag.attrs['class'] == ["infobox-label"] and dn.decode_name(tag.text) == t)
        if th:
            res = dn.decode_name(th.next_sibling.text)
            pos = res.find(' ')
            if pos != -1:
                pos1 = res.find('–', 0, pos) + 1
                res = res[pos1:pos] if pos1 != 0 else res[:pos]
            return dn.hours_minutes(int(res)) if res.isdigit() else None


def studios(part: BeautifulSoup) -> list[str] | None:
    """
    Извлечение студий anime из соответствующей части инфо-блока в WP.
    :param part: Часть страницы anime в WP (HTML-код).
    :return: Список студий anime в WP либо None.
    """
    th = part.find(lambda tag: tag.name == "th" and tag.has_attr("class")
                               and tag.attrs['class'] == ["infobox-label"] and tag.text == "Studio"
                               or tag.text == "Productioncompany")
    if th:
        td = th.next_sibling
        ul = td.ul
        res = []
        if ul:
            for li in ul.contents:
                res.append(dn.decode_name(li.text))
        else:
            for t in td.text.split("\n"):
                res.append(dn.decode_name(t))
        return res


def extraction_anime(part: dict[str, BeautifulSoup | dict[str, str]], tit: str
                     ) -> dict[str, str | int | list[str] | list[dict[str, str]] | None]:
    """
    Извлечение данных по anime из соответствующей части инфо-блока в WP.
    :param part: Часть страницы anime в WP (HTML-код).
    :param tit: Заголовок страницы.
    :return: Словарь данных по anime в WP:
    {
        'name_orig': str | None,
        'name_rom': str | None,
        'name_eng': str,
        'format': str | None,
        'number_of_episodes': int,
        'duration': str | None,
        'date_of_premiere': str | None,
        'studio': list[str] | None,
        'director': list[dict[str, str] | None],
        'poster': str | None
    }
    """
    print("- " * 3, "wp.extraction_anime")
    result = {
        'name_orig': title_orig(part),
        'name_rom': part['titles']['rom'] if "titles" in part and "rom" in part['titles'] else None,
        'name_eng': part['titles']['eng'] if "titles" in part and "eng" in part['titles'] else tit,
        'format': anime_format(part['page_part']),
        'number_of_episodes': number_of_episodes(part['page_part']),
        'duration': duration(part['page_part']),
        'date_of_premiere': date_of_premiere(part['page_part']),
        'studio': studios(part['page_part']),
        'director': authors(part['page_part'], "Directed"),
        'poster': poster(part['page_part'])
    }
    return result


def extraction_data(page_parts: dict[str, dict[str, dict[str, BeautifulSoup | dict[str, str]]]]
                    ) -> dict[str, dict[str, str | int | list[str | None] | list[dict[str, str] | None] | None]]:
    """
    Извлечение данных из частей инфо-блоков в WP.
    :param page_parts: Словарь частей страниц — результат filter_page_parts.
    :return: Словарь словарей данных по манге и anime в WP.
    """
    print("wp.extraction_data(page_parts)")
    res = {}
    for am, pages in page_parts.items():
        print("- ", am)
        if am not in res:
            res[am] = {}
        for tit, page_part in pages.items():
            print("- " * 2, tit)
            res[am][tit] = (extraction_anime(page_part, tit) if am == A else extraction_manga(page_part, tit))
    return res
