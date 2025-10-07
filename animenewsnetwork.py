"""
Поиск страниц в AnimeNewsNetwork (далее — ANN) и их обработка.
"""
import requests
from time import sleep
import dateutil.parser as date_parser

import decode_name as dn
from constants import *
from config import FORM_ANN, IGNORED_GENRES, GENRES_ANN, frequency


def xml(id_: int) -> str:
    """
    XML-страница манги или anime в ANN.
    :param id_: ID манги или anime.
    :return: XML-страница манги или anime в ANN.
    """
    sleep(1)
    return requests.get(f'{CANNE}api.xml', {'title': id_}).text


def manga_date_of_premiere(ann_xml: str) -> str | None:
    """
    Извлечение даты премьеры манги из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Дата премьеры или None.
    """
    pos = ann_xml.find(' type="Vintage"') + 15
    if pos == 14:
        return
    pos = ann_xml.find('>', pos) + 1
    if ann_xml[pos + 7:pos + 10] == '</i' or ann_xml[pos + 8:pos + 10] == 'to':
        return dn.month(ann_xml[pos:pos + 7])
    elif '(' in ann_xml[pos:pos + 10]:
        pos2 = ann_xml.find(" ", pos)
    else:
        pos2 = pos + 10
    date = ann_xml[pos:pos2]
    if len(date) == 4:
        date += '-12-31'
    elif len(date_ := date.strip().split()) > 1:
        date = date_[0] + '-12-31'
    dp = date_parser.parse(date).strftime('%Y-%m-%d')
    if dp != date:
        return
    return date


def pages(animes: dict[int, str], mangas: dict[int, str]) -> tuple[dict[int, str], dict[int, str], dict[int, int]]:
    """
    Поиск и получение XML-страниц манги и anime в ANN на базе уже полученных XML-страниц.
    :param animes: Словарь {ID: XML} уже полученных в search_pages anime.
    :param mangas: Словарь {ID: XML} уже полученных в search_pages манги.
    :return: Кортеж: словарь {ID: XML} anime, словарь {ID: XML} манги,
        словарь {ID anime: ID манги} адаптационных связей.
    """
    def apages(anime: str, aid: int) -> None:
        """
        Обработка XML-страницы anime, получение и добавление в соответствующие словари связанных XML-страниц.
        :param anime: XML-страница anime.
        :param aid: ID anime.
        """
        nonlocal animes_, mangas_, rm
        pos = 0
        while True:
            pos1 = anime.find('<related-', pos)
            if pos1 == -1:
                break
            pose = anime.find('/>', pos1)
            pos = anime.find('id=', pos1, pose) + 4
            id_ = int(anime[pos:anime.find('"', pos, pose)])
            pos = anime.find('rel=', pos1, pose) + 5
            if 'adapt' in anime[pos:anime.find('"', pos, pose)]:
                manga = xml(id_)
                posa = manga.find('<manga ')
                rm[aid] = id_
                if posa != -1 and id_ not in mangas and id_ not in mangas_:
                    mangas_[id_] = manga
                    mpages(manga)
            elif id_ not in animes and id_ not in animes_:
                animes_[id_] = xml(id_)
                apages(animes_[id_], id_)

    def mpages(manga: str) -> None:
        """
        Обработка XML-страницы манги, получение и добавление в соответствующие словари связанных XML-страниц.
        :param manga: XML-страница манги.
        """
        nonlocal animes_, mangas_
        pos = 0
        while True:
            pos1 = manga.find('<related-', pos)
            if pos1 == -1:
                break
            pose = manga.find('/>', pos1)
            if manga.find('serialized', pos1, pose) != -1:
                pos = pos1 + 9
                continue
            posa = manga.find('adapted', pos1, pose)
            posb = manga.find('adaptation', pos1, pose)
            if posa != -1 or posb != -1:
                pos = manga.find('id=', pos1, pose) + 4
                id_ = int(manga[pos:manga.find('"', pos, pose)])
                anime = xml(id_)
                posa = anime.find('<anime ')
                if posa != -1 and id_ not in animes_:
                    animes_[id_] = anime
                    apages(anime, id_)
                continue
            pos = manga.find('id=', pos1, pose) + 4
            id_ = int(manga[pos:manga.find('"', pos, pose)])
            if id_ not in mangas and id_ not in mangas_:
                mangas_[id_] = xml(id_)
                mpages(mangas_[id_])

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
                 ) -> tuple[dict[int, str], dict[int, str], dict[int, int]]:
    """
    Первичный поиск XML-страниц манги и anime в ANN, передача результатов в функцию pages и возврат её результатов.
    :param search: Наименование манги или anime.
    :param year: Год премьеры манги или anime.
    :param form: Формат anime (для манги не указывается (None)).
    :return: Кортеж: словарь {ID: XML} anime, словарь {ID: XML} манги,
        словарь {ID anime: ID манги} адаптационных связей.
    """
    def pars() -> tuple[int, str, str]:
        """
        Извлечение ID, фрагмента HTML текста строки и нормализованного наименования из поискового ответа ANN.
        :return: Кортеж: ID, фрагмент HTML текста строки, нормализованное наименование.
        """
        nonlocal pos
        pos = data.find('?id=', pos) + 4
        pos1 = data.find('"', pos)
        id_ = int(data[pos:pos1])
        pos = pos1 + 2
        pos1 = data.find('</a>', pos)
        text = data[pos:pos1]
        i = text.find('<i>')
        t = text[:text.find('<i>')] if i != -1 else text
        t = dn.normal_name(t.replace('<b>', '').replace('</b>', ''))
        return id_, text, t

    def val_year(_id: int, am: bool = False) -> bool:
        """
        Сверка года премьеры манги или anime из поискового ответа ANN (по ID) с заданным годом.
        :param _id: ID манги или anime.
        :param am: Переключатель anime/манга (False/True).
        :return: True — год не соответствует; False — год соответствует.
        """
        page = xml(_id)
        y = manga_date_of_premiere(page) if am else anime_date_of_premiere(page)
        return int(y[:4]) != year if y else False

    search_ = dn.normal_name(search)
    data = requests.get(f'{SANNE}search/name', {'q': search_}).text
    animes = {}
    mangas = {}
    pos = data.find(f'<strong>{search_}</strong>') + len(search_) + 15
    pose = data.find('<!--', pos)
    while True:
        pos = data.find(' <a ', pos + 4, pose)
        if pos == -1:
            break
        if data[pos - 5:pos] == A:
            aid, text, t = pars()
            if search_ not in t:
                break
            t = text[text.find('<i>') + 5:text.find('</i>') - 1].split()
            if 'live-action' in t or (form and form != FORM_ANN[t[0]]) or val_year(aid):
                continue
            animes[aid] = xml(aid)
        elif data[pos - 5:pos] == M:
            mid, text, t = pars()
            if search_ not in t:
                break
            pos1 = text.find('<i>') + 5
            if pos1 != 4:
                t = text[pos1:text.find('</i>') - 1]
                if 'novel' in t:
                    continue
            if t.find(search_) == 0 and not val_year(mid, True):
                mangas[mid] = xml(mid)
    return pages(animes, mangas)


def title(ann_xml: str, lang: str) -> str:
    """
    Извлечение наименования из XML-страницы в ANN.
    :param ann_xml: XML-страница.
    :param lang: Язык наименования: "orig", "eng", "rom", "rus".
    :return: Наименование или пустая строка, если не найдено наименование.
    """
    if lang == 'rom':
        pos1 = ann_xml.find('type="Main title" lang="') + 28
        if pos1 == 27:
            return ''
        pos2 = ann_xml.find('</info>', pos1)
        return ann_xml[pos1:pos2]
    langs = {'orig': 'JA', 'eng': 'EN', 'rus': 'RU'}
    pos1 = 0
    while True:
        pos1 = ann_xml.find('type="Alternative title"', pos1)
        if pos1 == -1:
            pos1 = ann_xml.find(f'lang="{langs[lang]}"') + 10
            if pos1 == 9:
                return ''
            pos2 = ann_xml.find('</info>', pos1)
            return ann_xml[pos1:pos2]
        pos2 = ann_xml.find('</info>', pos1)
        pos1 = ann_xml.find(f'lang="{langs[lang]}"', pos1, pos2) + 10
        if pos1 != 9:
            return ann_xml[pos1:pos2]
        pos1 = pos2


def html(page: str, params: dict) -> str:
    """
    Страница (HTML-код) в ANN.
    :param page: Имя PHP-модуля.
    :param params: GET-параметры.
    :return: Страница (HTML-код) в ANN.
    """
    sleep(1)
    return requests.get(f'{SANNE}{page}.php', params).text


def authors(ann_xml: str, am: bool = False) -> list[dict[str, str] | None]:
    """
    Извлечение авторов манги из XML-страницы в ANN.
    :param ann_xml: XML-страница.
    :param am: Переключатель: anime/манга (False/True).
    :return: Список авторов манги (автор — словарь имён: оригинальное, ромадзи или английское), если найдены.
        Если авторы не найдены, то список пустой.
    """
    staffs = ('<task>Story &amp; Art</task>', '<task>Story</task>', '<task>Original creator</task>', '<task>Art</task>'
              ) if am else ('<task>Director</task>',)
    result = []
    for staff in staffs:
        pos, posa, posb = 0, 0, 0
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
        ann_page = html('people', {'id': pid})
        pos = ann_page.find('<h1 id="page_header" class="same-width-as-main">') + 49
        pose = ann_page.find('</div>', pos)
        pos2 = ann_page.find('</h1>', pos, pose)
        name_rom_ = ann_page[pos:pos2].strip().split()
        name_rom = dn.normal_name(name_rom_[1].lower()).title() + ' ' + dn.normal_name(name_rom_[0].lower()).title()
        name_orig = ann_page[pos2 + 6:pose].strip()
        result.append({'name_orig': name_orig, 'name_rom': name_rom})
    return result


def number_of_volumes(ann_xml: str) -> int | None:
    """
    Извлечение количества томов манги из XML-страницы в ANN.
    :param ann_xml: XML-страница манги в ANN.
    :return: Количество томов манги. Если нет соответствующего поля — None.
    """
    pos = ann_xml.find('Number of tankoubon') + 21
    if pos != 20:
        return int(ann_xml[pos:ann_xml.find('<', pos)])


def publication(mid: int, ann_xml: str) -> dict[int, dict[str, str]] | None:
    """
    Извлечение издания манги из XML-страницы в ANN.
    :param mid: ID манги в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Словарь словарей {ID: {издание, издательство}} или None.
    """
    def publishing() -> str | None:
        """
        Извлечение наименования издательства.
        :return: Наименование издательства или None.
        """
        pos = m_html.find('<b>Publisher</b>') + 17
        if pos == 16:
            return
        pos2 = pos
        while pos2 == pos:
            pos = m_html.find('>', pos) + 1
            pos2 = m_html.find('<', pos)
        return m_html[pos:pos2]

    m_html = html(M, {'id': mid})
    result = {}
    pos = m_html.find('<div id="infotype-related">') + 27
    pose = m_html.find('</div>', pos)
    pos = m_html.find('serialized in', pos, pose)
    id_ = 0
    if pos != -1:
        pos = m_html.find(f'{M}.php?id=', pos, pose) + 13
        id_ = int(m_html[pos:m_html.find('"', pos, pose)])
    pos1 = ann_xml.find('type="Vintage"') + 15
    pose = min([ann_xml.find(s, pos1) for s in ('<ratings ', '<review ', '<news ', '<staff ')
                if ann_xml.find(s, pos1) > 0])
    pos = ann_xml.find('serialized in ', pos1, pose) + 14
    if pos == 13:
        publishing_ = publishing()
        if publishing_:
            result[id_] = {'publication': f'? ({publishing_})', 'publishing': publishing_, 'type': 2}
    else:
        pos2 = ann_xml.find(', ', pos, pose)
        if pos2 == -1:
            pos2 = ann_xml.find(')', pos, pose)
        publishing_ = publishing()
        if publishing_:
            result[id_] = {'publication': (frequency(dn.o_ou(ann_xml[pos:pos2])).
                                           replace("Gekkan Shounen Sunday", "Gekkan Shounen Magazine")),
                           'publishing': publishing_, 'type': 1}
    return result if len(result) else None


def genres(ann_xml: str) -> list[str]:
    """
    Извлечение жанров из XML-страницы в ANN.
    Если найден жанр, отсутствующий в словаре GENRES_ANN, запрашивается у пользователя наименование жанра на русском.
    Новый жанр сохраняется в файл new_genres.txt.
    :param ann_xml: XML-страница в ANN.
    :return: Список жанров.
    """
    pos = 1
    result = []
    new_genres = {}
    while True:
        pos = ann_xml.find('type="Genres">', pos) + 14
        if pos == 13:
            break
        genre = ann_xml[pos:ann_xml.find('</info>', pos)]
        if genre.title() not in IGNORED_GENRES:
            if genre in GENRES_ANN:
                result.append(GENRES_ANN[genre])
            else:
                with open('new_genres.txt', 'r', encoding='utf8') as file:
                    ng = file.readlines()
                for g in ng:
                    if ' ' in g and g[:g.find(':')] == genre:
                        result.append(g[g.find(':') + 2:-1])
                        break
                else:
                    print('Новый жанр в ANN!', genre)
                    add = input('Добавить жанр? Y/N: ')
                    if add == 'Y' or add == 'y':
                        new_genre = input('Наименование жанра на русском: ')
                        result.append(new_genre)
                        new_genres[genre] = new_genre
    if len(new_genres):
        txt = 'ANN\n'
        for ag, g in new_genres.items():
            txt += f'{ag}: {g}\n'
        with open('new_genres.txt', 'a', encoding='utf8') as file:
            file.write(txt)
        print('Перенесите новые жанры в «config.py» из «new_genres.txt».')
    return result


def poster(ann_xml: str) -> str | None:
    """
    Извлечение ссылки на постер из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Ссылка на постер в ANN или None.
    """
    pos = ann_xml.find(' type="Picture"') + 15
    if pos == 14:
        return
    pos2 = ann_xml.find('>', pos)
    pos = ann_xml.find(' src="', pos, pos2) + 6
    return ann_xml[pos:ann_xml.find('"', pos, pos2)]


def extraction_manga(
        mid: int, ann_xml: str
) -> dict[str, str | list[dict[str, str] | None] | int | dict[int, dict[str, str]] | list[str] | None]:
    """
    Извлечение данных манги из XML-страницы в ANN.
    :param mid: ID манги в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Словарь данных манги в ANN.
    """
    result = {
        'name_orig': title(ann_xml, 'orig'),
        'name_rom': title(ann_xml, 'rom'),
        'name_eng': title(ann_xml, 'eng'),
        'name_rus': title(ann_xml, 'rus'),
        'author_of_manga': authors(ann_xml, True),
        'number_of_volumes': number_of_volumes(ann_xml),
        'date_of_premiere': manga_date_of_premiere(ann_xml),
        'publication': publication(mid, ann_xml),
        'genre': genres(ann_xml),
        'poster': poster(ann_xml)
    }
    if not result['name_orig']:
        result['name_orig'] = result['name_rom']
    return result


def anime_format(ann_xml: str) -> str:
    """
    Извлечение формата anime из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Формат anime.
    """
    pos = ann_xml.find('<anime') + 6
    pos2 = ann_xml.find('>', pos)
    pos = ann_xml.find(' type="', pos, pos2) + 7
    if pos == 6:
        pos = ann_xml.find(' precision="', pos, pos2) + 12
    return FORM_ANN[ann_xml[pos:ann_xml.find('"', pos, pos2)]]


def number_of_episodes(ann_xml: str) -> int:
    """
    Извлечение количества эпизодов anime из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Количество эпизодов anime в ANN.
    """
    pos = ann_xml.find(' type="Number of episodes"') + 26
    if pos != 25:
        pos = ann_xml.find('>', pos) + 1
        return int(ann_xml[pos:ann_xml.find('<', pos)])
    else:
        return 1


def duration(ann_xml: str) -> str | None:
    """
    Извлечение продолжительности эпизода anime из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Продолжительность эпизода anime в ANN или None.
    """
    pos = ann_xml.find(' type="Running time"') + 20
    if pos != 19:
        pos = ann_xml.find('>', pos) + 1
        res = ann_xml[pos:ann_xml.find('<', pos)]
        if 'hour' in res.lower():
            t = res.split()
            if len(t) > 1:
                if t[0].lower() == 'one':
                    res = 60
                elif t[0].lower() == 'half':
                    res = 30
        return dn.hours_minutes(int(res))


def anime_date_of_premiere(ann_xml: str) -> str | None:
    """
    Извлечение даты премьеры anime из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :return: Дата премьеры anime в ANN или None.
    """
    pos = ann_xml.find(' type="Premiere date"') + 21
    if pos == 20:
        pos = ann_xml.find(' type="Vintage"') + 15
    pos = ann_xml.find('>', pos) + 1
    date = ann_xml[pos:pos + 10]
    if '</' in date:
        date = date[:date.find('</')]
        date_ = date.strip().split()
        if len(date_) > 1 or len(date) == 4:
            date = date_[0] + '-12-31'
    dp = date_parser.parse(date).strftime('%Y-%m-%d')
    if dp != date:
        return
    return date


def extraction_anime(ann_xml: str, mid: int | None = None) -> dict[str, str | int | list[dict[str, str] | str] | None]:
    """
    Извлечение данных anime из XML-страницы в ANN.
    :param ann_xml: XML-страница в ANN.
    :param mid: ID манги в ANN.
    :return: Словарь данных anime в ANN.
    """
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
    if not result['name_orig']:
        result['name_orig'] = result['name_rom']
    if mid:
        result[M + '_id'] = mid
    return result
