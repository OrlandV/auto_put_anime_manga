"""
Поиск страниц в AnimeNewsNetwork (далее — ANN) и их обработка.
"""
import xml.etree.ElementTree as et
from urllib.parse import quote
from bs4 import BeautifulSoup
from bs4.element import NavigableString
import dateutil.parser as date_parser
from html import unescape

from constants import *
from file_cache import anti_bot, NewGenre
import decode_name as dn
from config import FORM_ANN, IGNORED_GENRES, GENRES_ANN, frequency


def xml(id_: int) -> et.Element | None:
    """
    XML-страница манги или anime в ANN.
    :param id_: ID манги или anime.
    :return: XML-страница манги или anime в ANN.
    """
    print(f"ann.xml({id_})")
    return et.fromstring(anti_bot("ANN", f"{CANNE}api.xml?title={id_}", "xml"))


def html(page: str, params: dict, _php: bool = True) -> BeautifulSoup:
    """
    Страница (HTML-код) в ANN.
    :param page: Путь модуля после «https://www.animenewsnetwork.com/encyclopedia/» до «.php» (если есть).
    :param params: GET-параметры.
    :param _php: Флаг включения расширения «.php» в адрес.
    :return: Страница (HTML-код) в ANN.
    """
    url = f"{SANNE}{page}{".php" if _php else ""}{"?" if len(params) else ""}"
    for k, v in params.items():
        url += f"{k}={quote(str(v))}&"
    return BeautifulSoup(anti_bot("ANN", url[:-1]), "html.parser")


def manga_date_of_premiere(ann_xml: et.Element) -> str | None:
    """
    Извлечение даты премьеры манги из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Дата премьеры или None.
    """
    if (info := ann_xml[0].find("././info[@type='Vintage']")) is not None:
        date = info.text
        ld = len(date)
        dfs = date.find(" ")
        if ld in (4, 7) or "to" in date:
            if 7 in (ld, dfs):
                return dn.month(date[:7])
            if 4 in (ld, dfs):
                return date[:4] + "-12-31"
        date = date[:date.find(" ") if "(" in date else 10]
        if len(date_ := date.strip().split()) > 1:
            date += date_[0] + "-12-31"
        dp = date_parser.parse(date).strftime("%Y-%m-%d")
        if dp == date:
            return date


def anime_date_of_premiere(ann_xml: et.Element) -> str | None:
    """
    Извлечение даты премьеры anime из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Дата премьеры anime в ANN или None.
    """
    info = ann_xml[0].find("././info[@type='Premiere date']") or ann_xml[0].find("././info[@type='Vintage']")
    date = info.text[:10]
    if len(dl := date.strip().split(" ")) > 1 and not dl[1].isdigit() or len(date) == 4:
        date = dl[0] + "-12-31"
    dp = date_parser.parse(date).strftime('%Y-%m-%d')
    if dp == date:
        return date


def pages(animes: dict[int, et.Element], mangas: dict[int, et.Element]
          ) -> tuple[dict[int, et.Element], dict[int, et.Element], dict[int, int]]:
    """
    Поиск и получение XML-страниц манги и anime в ANN на базе уже полученных XML-страниц.
    :param animes: Словарь {ID: XML} уже полученных в search_pages anime.
    :param mangas: Словарь {ID: XML} уже полученных в search_pages манги.
    :return: Кортеж: словарь {ID: XML} anime, словарь {ID: XML} манги,
        словарь {ID anime: ID манги} адаптационных связей.
    """
    def apages(anime: et.Element, aid: int) -> None:
        """
        Обработка XML-страницы anime, получение и добавление в соответствующие словари связанных XML-страниц.
        :param anime: XML-страница anime.
        :param aid: ID anime.
        """
        nonlocal animes_, mangas_, rm
        rels = anime[0].findall("related-prev")
        rels.extend(anime[0].findall("related-next"))
        for rel in rels:
            if rel.attrib['rel'] == "part of":
                continue
            id_ = int(rel.attrib['id'])
            if id_ in mangas or id_ in mangas_ or id_ in animes or id_ in animes_:
                continue
            if (rel.attrib['rel'] in ("adaptation", "adapted from", "alternate retelling", "alternate retelling of",
                                       "compilation of", "prequel", "sequel", "sequel of")
                    and id_ not in animes and id_ not in mangas and id_ not in mangas_ and id_ not in animes_):
                xml_ = xml(id_)
                if xml_.find("manga") is not None:
                    rm[aid] = id_
                    mangas_[id_] = xml_
                    mpages(xml_)
                elif xml_.find("anime") is not None:
                    animes_[id_] = xml_
                    apages(xml_, id_)

    def mpages(manga: et.Element) -> None:
        """
        Обработка XML-страницы манги, получение и добавление в соответствующие словари связанных XML-страниц.
        :param manga: XML-страница манги.
        """
        nonlocal animes_, mangas_
        rels = manga[0].findall("related-prev")
        rels.extend(manga[0].findall("related-next"))
        for rel in rels:
            if rel.attrib['rel'] == "serialized in":
                continue
            id_ = int(rel.attrib['id'])
            if (rel.attrib['rel'] in ("adaptation", "adapted", "alternate retelling", "compilation", "spinoff",
                                      "spinoff of")
                    and id_ not in animes and id_ not in mangas and id_ not in animes_ and id_ not in mangas_):
                xml_ = xml(id_)
                if xml_.find("anime") is not None:
                    animes_[id_] = xml_
                    apages(xml_, id_)
                elif xml_.find("manga") is not None:
                    mangas_[id_] = xml_
                    mpages(xml_)

    print(f"ann.pages(animes, mangas)")
    animes_ = {}
    mangas_ = {}
    rm = {}
    for _aid, _anime in animes.items():
        animes_[_aid] = _anime
        apages(_anime, _aid)
    for _mid, _manga in mangas.items():
        mangas_[_mid] = _manga
        mpages(_manga)
    return animes_, mangas_, rm


def search_pages(search: str, year: int | None = None, form: str | None = None
                 ) -> tuple[dict[int, et.Element], dict[int, et.Element], dict[int, int]]:
    """
    Первичный поиск XML-страниц манги и anime в ANN, передача результатов в функцию pages и возврат её результатов.
    :param search: Наименование манги или anime.
    :param year: Год премьеры манги или anime.
    :param form: Формат anime (для манги не указывается (None)).
    :return: Кортеж: словарь {ID: XML} anime, словарь {ID: XML} манги,
        словарь {ID anime: ID манги} адаптационных связей.
    """
    def pars() -> tuple[int, str]:
        """
        Извлечение ID, фрагмента HTML текста строки и нормализованного наименования из поискового ответа ANN.
        :return: Кортеж: ID, нормализованное наименование.
        """
        pe = a.text.find(" (")
        t = a.text if pe < 0 else a.text[:pe]
        return int(a.attrs['href'].split("?id=")[1]), dn.normal_name(t)

    def val_year(_am: bool = False) -> bool:
        """
        Сверка года премьеры манги или anime из поискового ответа ANN (по ID) с заданным годом.
        :param _am: Переключатель anime/манга (False/True).
        :return: True — год не соответствует; False — год соответствует.
        """
        y = manga_date_of_premiere(page) if _am else anime_date_of_premiere(page)
        return int(y[:4]) == year if y else False

    print(f"ann.search_pages('{search}', {year}, '{form}')")
    search_ = dn.normal_name(search)
    data = html("search/name", {'q': search_}, False)
    animes = {}
    mangas = {}
    a = data.find(lambda tag: tag.name == "strong" and tag.text == search_)
    nr = a.previous_sibling.text
    nr = nr[:nr.find(" ")]
    if nr.isdigit():
        for _ in range(int(nr)):
            a = a.find_next("a")
            am = a.previous_sibling.text.strip()
            id_, t = pars()
            if search_ not in t:
                break
            if am == A:
                t = a.i.text[2:-1].split()
                if "live-action" not in t and "novel" not in t and "stalled" not in t:
                    page = xml(id_)
                    if form and form == FORM_ANN[t[0]] and val_year():
                        animes[id_] = page
            elif am == M and "novel" not in a.text and t.find(search_) == 0:
                page = xml(id_)
                if not val_year(True):
                    mangas[id_] = page
    return pages(animes, mangas)


def title(ann_xml: et.Element, lang: str) -> str:
    """
    Извлечение наименования из XML-страницы в ANN.
    :param ann_xml: XML-страница.
    :param lang: Язык наименования: "orig", "rom", "eng", "rus".
    :return: Наименование или пустая строка, если не найдено наименование.
    """
    langs = {'orig': "JA", 'rom': "JA", 'eng': "EN", 'rus': "RU"}
    if (info := ann_xml[0].find("././info[@type='Main title']")) is not None:
        if info.attrib['lang'] == (langs[lang] if lang in ("rom", "eng") else ""):
            return info.text
    info = ann_xml[0].findall(f"././info[@type='Alternative title'][@lang='{langs[lang]}']")
    return unescape(info[0 if lang == "rom" else -1].text) if len(info) else ""


def authors(ann_xml: et.Element, am: bool = False) -> list[dict[str, str] | None]:
    """
    Извлечение авторов манги или режиссёров anime из XML-страницы в ANN.
    :param ann_xml: XML-страница.
    :param am: Переключатель: anime/манга (False/True).
    :return: Список авторов манги (автор — словарь имён: оригинальное, ромадзи или английское), если найдены.
        Если авторы не найдены, то список пустой.
    """
    staffs = ("Story & Art", "Story", "Original creator", "Art", "Original Character Design"
              ) if am else ("Chief Director", "Director")
    result = []
    for staff in staffs:
        if (person := ann_xml[0].find(f"././staff[task='{staff}']/person")) is not None:
            page = html("people", {'id': person.attrib['id']})
            h1 = page.find("h1", {'id': "page_header"})
            name_rom_ = h1.text.strip().split()
            name_rom = ((dn.normal_name(name_rom_[1].lower()).title() + " " if len(name_rom_) > 1 else "")
                        + dn.normal_name(name_rom_[0].lower()).title())
            name_orig = h1.next_sibling.strip()
            if not name_orig:
                for i in ("3", "2"):
                    if div := h1.find_next("div", {'id': f"infotype-1{i}"}):
                        name_orig += div.span.text + (" " if i == "3" else "")
            result.append({'name_orig': unescape(name_orig), 'name_rom': name_rom} if name_orig else
                          {'name_rom': name_rom})
    return result


def number_of_volumes(ann_xml: et.Element) -> int | None:
    """
    Извлечение количества томов манги из XML-страницы в ANN.
    :param ann_xml: XML-страница манги в ANN.
    :return: Количество томов манги. Если нет соответствующего поля — None.
    """
    if (info := ann_xml[0].find("././info[@type='Number of tankoubon']")) is not None:
        return int(info.text)


def publication(ann_xml: et.Element) -> dict[int, dict[str, str]] | None:
    """
    Извлечение издания манги из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Словарь словарей {ID: {издание, издательство}} или None.
    """
    def publishing(f_id: bool = False) -> str | tuple[str, int] | None:
        """
        Извлечение наименования издательства.
        :param f_id: Флаг возвращения ID издательства.
        :return: Наименование издательства и его ID (опционо) или None.
        """
        nonlocal m_html
        if not m_html:
            m_html = html(M, {'id': ann_xml[0].attrib['id']})
        b = m_html.find(lambda tag: tag.name == "table" and tag.has_attr("id") and tag.attrs['id'] == "credits")
        if b := b.find_next(lambda tag: tag.name == "b" and "Publisher" in tag.text or "Licensed by" in tag.text):
            a = b.parent.a
            return (a.text, int(a.attrs['href'].split("?id=")[1])) if f_id else a.text

    m_html = None
    if (rels := ann_xml[0].findall("././related-prev[@rel='serialized in']")) is not None:
        res = {}
        for rel in rels:
            id_ = int(rel.attrib['id'])
            m_html = html(M, {'id': id_})
            ps = [m_html.find("h1", {'id': "page_header"}).text.strip()[1:-1]]
            if (divs := m_html.find("div", {'id': "infotype-2"})) is not None:
                ps.extend([div.text.removesuffix(" (Japanese)") for div in divs.contents[3:-1]
                           if not isinstance(div, NavigableString) and " (Japanese)" in div.text
                           or " (" not in div.text])
            if len(ps) == 1:
                p = ps[0]
            else:
                text = ""
                for i, p in enumerate(ps):
                    text += f"\n{i + 1}. {p}"
                print(f"Укажите номер подходящего наименования издания «{ps[0]}»:{text}")
                while True:
                    num = input("Укажите номер: ")
                    if num.isdigit():
                        break
                    print("Ошибка! Требуется ввести целое число.")
                num = int(num)
                if not num:
                    return
                p = ps[num - 1]
            res[id_] = {
                'publication': (frequency(dn.o_ou(p)).replace("Gekkan Shounen Sunday", "Gekkan Shounen Magazine")),
                'publishing': publishing(),
                'type': 1
            }
        return res
    elif (info := ann_xml[0].find("././info[@type='Vintage']")) is not None:
        publication_ = info.text[info.text.find("serialized in ") + 14:info.text.find(")")]
        if publication_:
            if "<i>" in publication_:
                publication_ = publication_[3:publication_.find("</i>")]
            publishing_, id_ = publishing(True)
            return {id_: {'publication': publication_, 'publishing': publishing_, 'type': 1}}
        elif publishing_ := publishing():
            return {0: {'publication': f'? ({publishing_})', 'publishing': publishing_, 'type': 2}}


def genres(ann_xml: et.Element) -> list[str]:
    """
    Извлечение жанров из XML-страницы в ANN.
    Если найден жанр, отсутствующий в словаре GENRES_ANN, запрашивается у пользователя наименование жанра на русском.
    Новый жанр сохраняется в файл new_genres.txt.
    :param ann_xml: XML-страница в ANN.
    :return: Список жанров.
    """
    res = []
    for _genre in ann_xml[0].findall("././info[@type='Genres']"):
        genre = _genre.text
        if genre.title() not in IGNORED_GENRES:
            if genre in GENRES_ANN:
                res.append(GENRES_ANN[genre])
            else:
                ng = NewGenre("ANN")
                if new_genre := ng.search_or_add(genre):
                    res.append(new_genre)
    return res


def poster(ann_xml: et.Element) -> str | None:
    """
    Извлечение ссылки на постер из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Ссылка на постер в ANN или None.
    """
    if (info := ann_xml[0].find("././info[@type='Picture']")) is not None:
        return info.attrib['src']


def fix_name(result: dict[str, str | list[dict[str, str] | None] | int | dict[int, dict[str, str]] | list[str] | None]
             ) -> dict[str, str | list[dict[str, str] | None] | int | dict[int, dict[str, str]] | list[str] | None]:
    """
    Коррекция наименований в словаре данных манги или anime в ANN.
    :param result: Словарь данных манги или anime в ANN.
    :return: Словарь данных манги или anime в ANN.
    """
    if not result['name_orig']:
        if result['name_rom']:
            result['name_orig'] = result['name_rom']
        else:
            result['name_orig'] = result['name_rom'] = result['name_eng']
    elif result['name_orig'] == result['name_rom'] and result['name_rom'] != result['name_eng']:
        result['name_rom'] = result['name_eng']
    return result


def extraction_manga(
        mid: int, ann_xml: et.Element
) -> dict[str, str | list[dict[str, str] | None] | int | dict[int, dict[str, str]] | list[str] | None]:
    """
    Извлечение данных манги из XML-страницы в ANN.
    :param mid: ID манги в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Словарь данных манги в ANN.
    """
    print(f"- ann.extraction_manga({mid}, ann_xml):")
    result = {
        'name_orig': title(ann_xml, 'orig'),
        'name_rom': title(ann_xml, 'rom'),
        'name_eng': title(ann_xml, 'eng'),
        'name_rus': title(ann_xml, 'rus'),
        'author_of_manga': authors(ann_xml, True),
        'number_of_volumes': number_of_volumes(ann_xml),
        'date_of_premiere': manga_date_of_premiere(ann_xml),
        'publication': publication(ann_xml),
        'genre': genres(ann_xml),
        'poster': poster(ann_xml)
    }
    result = fix_name(result)
    print(result['name_rom'])
    return result


def anime_format(ann_xml: et.Element) -> str:
    """
    Извлечение формата anime из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Формат anime.
    """
    return FORM_ANN[ann_xml[0].attrib['type'] or ann_xml[0].attrib['precision']]


def number_of_episodes(ann_xml: et.Element) -> int:
    """
    Извлечение количества эпизодов anime из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Количество эпизодов anime в ANN.
    """
    if (info := ann_xml[0].find("././info[@type='Number of episodes']")) is not None:
        res = info.text
        if " " in res:
            res = res[:res.find(" ")]
        return int(res)
    return 1


def duration(ann_xml: et.Element) -> str | None:
    """
    Извлечение продолжительности эпизода anime из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Продолжительность эпизода anime в ANN или None.
    """
    if (info := ann_xml[0].find("././info[@type='Running time']")) is not None:
        res = info.text
        if "hour" in res.lower():
            t = res.split()
            if t[0].lower() == "one":
                res = 60
            elif t[0].lower() == "half":
                res = 30
        return dn.hours_minutes(int(res))


def extraction_anime(ann_xml: et.Element, mid: int | None = None
                     ) -> dict[str, str | int | list[dict[str, str] | str] | None]:
    """
    Извлечение данных anime из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :param mid: ID манги в ANN.
    :return: Словарь данных anime в ANN.
    """
    print(f"- ann.extraction_anime(ann_xml, {mid}):")
    result = {
        'name_orig': title(ann_xml, 'orig'),
        'name_rom': title(ann_xml, 'rom'),
        'name_eng': title(ann_xml, 'eng'),
        'name_rus': title(ann_xml, 'rus'),
        'format': anime_format(ann_xml),
        'number_of_episodes': number_of_episodes(ann_xml),
        'duration': duration(ann_xml),
        'date_of_premiere': anime_date_of_premiere(ann_xml),
        'director': authors(ann_xml),
        'genre': genres(ann_xml),
        'poster': poster(ann_xml)
    }
    result = fix_name(result)
    if mid:
        result[M + '_id'] = mid
    print(result['name_rom'])
    return result
