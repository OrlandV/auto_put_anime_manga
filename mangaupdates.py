"""
Поиск страниц в MangaUpdates (далее — MU) и их обработка.
"""
import json
from time import sleep
import requests

from decode_name import normal_name
from constants import *
from config import IGNORED_GENRES, GENRES_MU


def manga_json(mu_id: int) -> json.JSONEncoder | None:
    """
    Получение данных по манге в MU.
    Если за 5 попыток нет результата — возвращается None.
    :param mu_id: ID манги в MU.
    :return: Данные по манге в MU в JSON-формате, либо None.
    """
    b = 0
    while True:
        sleep(1)
        try:
            result = requests.get(f'{AMUS}{mu_id}').json()
        except requests.Timeout:
            b += 1
            if b == 5:
                return
            continue
        return result


def search_pages_id(mangas: dict[int, json.JSONEncoder] | None, mu_id: int) -> dict[int, json.JSONEncoder] | None:
    """
    Получение данных по манге из MU, включая по связанной манге.
    :param mangas: Словарь {ID: JSON} полных JSON-словарей данных по манге в MU.
    :param mu_id: ID манги в MU.
    :return: Словарь {ID: JSON} полных JSON-словарей данных по манге в MU, либо None.
    """
    manga = manga_json(mu_id)
    if manga:
        if not mangas:
            mangas = {}
        mangas[mu_id] = manga
        for rs in manga['related_series']:
            if (rs['related_series_id'] not in mangas and 'related_series_name' in rs and
                    rs['related_series_name'] and '(Novel)' not in rs['related_series_name']):
               mangas = search_pages_id(mangas, rs['related_series_id'])
        return mangas


def search_pages(search: str, year: int | None = None) -> dict[int, json.JSONEncoder] | None:
    """
    Первичный поиск данных по манге в MU, выявление в JSON-ответе (данных по манге) связей с продолжением,
    предысторией и ответвлений манги, и возврат словаря словарей (JSON).
    :param search: Поисковый запрос — наименование искомой манги.
    :param year: Год премьеры манги, если известен.
    :return: Словарь {ID: JSON} полных JSON-словарей данных по манге в MU.
    """
    search = normal_name(search)
    sleep(1)
    data = requests.post(AMUS + 'search', {'search': search}).json()
    for res in data['results']:
        if search == normal_name(res['hit_title']):
            if year and int(res['record']['year']) != year:
                continue
            mangas = {}
            mangas = search_pages_id(mangas, res['record']['series_id'])
            return mangas


def title_rom(mu_json: json.JSONEncoder) -> str:
    """
    Извлечение ромадзи наименования манги из полного JSON-словаря данных по манге в MU.
    :param mu_json: Данные по манге в MU в JSON-формате.
    :return: Ромадзи наименование манги в MU.
    """
    return mu_json['title']


def date(mu_json: json.JSONEncoder) -> str:
    """
    Извлечение даты премьеры манги из полного JSON-словаря данных по манге в MU.
    Т.к. в MU указан только год, то к году добавляется «-12-31» для соответствия формату yyyy.mm.dd.
    Указание последнего года означает, что нет информации о точной дате,
    а при сортировке по дате неточная информация должна быть в конце.
    :param mu_json: Данные по манге в MU в JSON-формате.
    :return: Дата премьеры манги в MU.
    """
    return mu_json['year'] + '-12-31'


def volumes(mu_json: json.JSONEncoder) -> int:
    """
    Извлечение количества томов манги из полного JSON-словаря данных по манге в MU.
    Если вместо количества томов в JSON-словаре указано количество глав,
    то этот факт отмечается как отрицательное число в возвращаемом ответе функции.
    :param mu_json: Данные по манге в MU в JSON-формате.
    :return: Количество томов или количество глав (отрицательное число) манги в MU.
    """
    p = mu_json['status'].find(' ')
    if len(mu_json['status']) and p != -1:
        n = int(mu_json['status'][:p])
    else:
        return 1
    if mu_json['status'][p + 1:p + 2] == 'V':
        return n
    return -n


def select_title(mu_json: json.JSONEncoder, lang: str) -> str:
    """
    Выбор наименования манги через обращение к пользователю.
    :param mu_json: Данные по манге в MU в JSON-формате.
    :param lang: Язык наименования: "orig", "eng", "rus".
    :return: Наименование манги в MU.
    """
    if lang == 'orig':
        lang = 'оригинальное'
    elif lang == 'eng':
        lang = 'английское'
    elif lang == 'rus':
        lang = 'русское'
    else:
        raise ValueError('Неверно указан язык.')
    titles = []
    text = f'\n0. *** Подходящего варианта нет ***\n1. {mu_json['title']}'
    for i, title in enumerate(mu_json['associated']):
        titles.append(title['title'])
        text += f'\n{i + 2}. {title['title']}'
    print(f'Выберите {lang} наименование манги «{mu_json['title']}»:{text}')
    while True:
        num = input('Укажите номер: ')
        if num.isdigit():
            num = int(num)
            break
        print('Ошибка! Требуется ввести целое число.')
    if not num:
        return ''
    elif num == 1:
        return mu_json['title']
    return titles[num - 2]


def authors_of_manga(mu_json: json.JSONEncoder) -> dict[int, dict[str, str]]:
    """
    Извлечение авторов манги из полного JSON-словаря данных по манге в MU.
    :param mu_json: Данные по манге в MU в JSON-формате.
    :return: Словарь {ID: Словарь_имён} словарей имён авторов манги в MU.
    """
    authors = {}
    for i, author in enumerate(mu_json['authors']):
        if author['type'] in ('Author', 'Artist'):
            if author['author_id']:
                sleep(1)
                author_json = requests.get(f'{AMUA}{author['author_id']}').json()
                pos = author_json['name'].find(' (')
                name_rom = author_json['name'][:pos] if pos != -1 else author_json['name']
                if author['author_id'] not in authors:
                    authors[author['author_id']] = {
                        'name_orig': author_json['actualname'],
                        'name_rom': name_rom.lower().title()
                    }
            else:
                authors[i] = {'name_rom': author['name'].lower().title()}
    return authors


def publications(mu_json: json.JSONEncoder) -> list[dict[str, str | int]] | None:
    """
    Извлечение изданий манги из полного JSON-словаря данных по манге в MU.
    :param mu_json: Данные по манге в MU в JSON-формате.
    :return: Список словарей изданий манги в MU в формате:
        - [{'publication': Издание, 'publishing': Издательство}] — для журнала (type=1),
        - [{'publication': ? (Издательство), 'publishing': Издательство, 'type': 2}] — для книг;
        либо None.
    """
    if 'publications' not in mu_json or 'publishers' not in mu_json:
        return
    res = []
    for publication in mu_json['publications']:
        res.append({'publication': (publication['publication_name'].replace("Afternoon", "Gekkan Afternoon").
                                    replace("Morning", "Shuukan Morning")),
                    'publishing': publication['publisher_name']})
    for i in range(len(res)):
        if not res[i]['publishing'] and mu_json['publishers'][i]['publisher_name']:
            res[i]['publishing'] = mu_json['publishers'][i]['publisher_name']
    if not len(res):
        for publisher in mu_json['publishers']:
            res.append({'publication': f'? ({publisher['publisher_name']})', 'publishing': publisher['publisher_name'],
                        'type': 2})
    return res


def genres(mu_json: json.JSONEncoder) -> list[str]:
    """
    Извлечение жанров манги из полного JSON-словаря данных по манге в MU.
    Если найден жанр, отсутствующий в словаре GENRES_MU, запрашивается у пользователя наименование жанра на русском.
    Новый жанр сохраняется в файл new_genres.txt.
    :param mu_json: Данные по манге в MU в JSON-формате.
    :return: Список жанров манги в MU.
    """
    result = []
    new_genres = {}
    for genre in mu_json['genres']:
        if genre['genre'] not in IGNORED_GENRES:
            if genre['genre'] in GENRES_MU:
                result.append(GENRES_MU[genre['genre']])
            else:
                with open('new_genres.txt', 'r', encoding='utf8') as file:
                    ng = file.readlines()
                for g in ng:
                    if ' ' in g and g[:g.find(':')] == genre['genre']:
                        result.append(g[g.find(':') + 2:-1])
                        break
                else:
                    print('Новый жанр в MangaUpdates!', genre['genre'])
                    add = input('Добавить жанр? Y/N: ')
                    if add == 'Y' or add == 'y':
                        new_genre = input('Наименование жанра на русском: ')
                        result.append(new_genre)
                        new_genres[genre['genre']] = new_genre
    if len(new_genres):
        txt = 'MU\n'
        for ag, g in new_genres.items():
            txt += f'{ag}: {g}\n'
        with open('new_genres.txt', 'a', encoding='utf8') as file:
            file.write(txt)
        print('Перенесите новые жанры в «config.py» из «new_genres.txt».')
    return result


def poster(mu_json: json.JSONEncoder) -> str | None:
    """
    Извлечение ссылки на постер из полного JSON-словаря данных по манге в MU.
    :param mu_json: Данные по манге в MU в JSON-формате.
    :return: Ссылка на постер в MU либо None.
    """
    return mu_json['image']['url']['original'] if 'image' in mu_json else None


def extraction_manga(mu_json: json.JSONEncoder
                     ) -> dict[str, str | dict[int, dict[str, str]] | int | dict[str, str] | list[str]]:
    """
    Извлечение данных по манге из полного JSON-словаря данных по манге в MU.
    :param mu_json: Данные по манге в MU в JSON-формате.
    :return: Словарь данных по манги в MU.
    """
    nv = volumes(mu_json)
    if nv < 0:
        nc = -nv
        nv = 1
    else:
        nc = nv
    res = {
        'name_orig': select_title(mu_json, 'orig'),
        'name_rom': title_rom(mu_json),
        'name_eng': select_title(mu_json, 'eng'),
        'name_rus': select_title(mu_json, 'rus'),
        'author_of_manga': authors_of_manga(mu_json),
        'number_of_volumes': nv,
        'number_of_chapters': nc,
        'date_of_premiere': date(mu_json),
        'publication': publications(mu_json),
        'genre': genres(mu_json),
        'poster': poster(mu_json)
    }
    if not res['name_orig']:
        res['name_orig'] = res['name_rom']
    return res
