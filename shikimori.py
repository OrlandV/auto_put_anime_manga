"""
Поиск данных в Shikimori (далее — SH) и их обработка.
"""
# import json
from shikimori_api import Shikimori

# from input import *
from config import FORM_WA_SH, FORM_SH_WA, IGNORED_GENRES, GENRES_SH
from decode_name import hours_minutes
from constants import SH


# OAuth
# def token_saver(token: dict):
#     with open('token.json', 'w') as f:
#         f.write(json.dumps(token))
#
#
# session = Shikimori('APP_NAME', client_id='CLIENT_ID', client_secret='CLIENT_SECRET', token_saver=token_saver)
#
# print(session.get_auth_url())
# code = input('Authorization Code: ')
# session.fetch_token(code)
#
# # After receiving and saving token, you can load it from file:
# with open('token.json') as f:
#     token = json.load(f)
# session = Shikimori('APP_NAME', client_id='CLIENT_ID', client_secret='CLIENT_SECRET',
#                     token=token, token_saver=token_saver)


session = Shikimori()
api = session.get_api()

external_links = None

# GET /api/animes?search=KonoSuba&kind=movie
# animes = api.animes.GET(search=title, kind=FORM_WA_SH[form], season=str(year))
# roles = api.animes(animes[0]['id']).roles.GET()
# d = []
# for r in roles:
#     if not r['character'] and "Director" in r['roles']:
#         d.append(r['person']['name'])
# print(animes[0]['name'])
# print(d)
# # GET /api/animes/1
# a1 = api.animes(1).GET()
# print(a1)
# # GET /api/animes/1/screenshots
# a1s = api.animes(1).screenshots.GET()
# print(a1s)


def search_anime(search: str, year: int, form: str
                 ) -> dict[int, dict[str, str | int | dict[str, str] | list[str | dict[str, int | str] | None] | None]]:
    """
    Поиск anime в SH.
    :param search: Наименование anime.
    :param year: Год премьеры.
    :param form: Формат.
    :return: Список словарей данных по anime в SH.
    """
    animes = api.animes.GET(search=search, season=str(year), kind=FORM_WA_SH[form])
    return {anime['id']: api.animes(anime['id']).GET() for anime in animes}


def ann_manga_id(manga: dict[str, str | int | dict[str, str] | list[str | dict[str, int | str] | None] | None] | None
                 ) -> int | None:
    """
    Извлечение ID манги в ANN по ссылке в SH.
    :param manga: Словарь данных по манге в SH.
    :return: ID манги в ANN, если найдена ссылка в SH. Иначе — None.
    """
    if manga:
        external_links = api.mangas(manga['id']).external_links.GET()
        for el in external_links:
            if el['kind'] == "anime_news_network":
                return int(el['url'][el['url'].find("?id=") + 4:])


def person(pid: int) -> dict[str, str]:
    """
    Извлечение персоны из SH.
    :param pid: ID персоны в SH.
    :return: Словарь персоны в SH.
    """
    p = api.people(pid).GET()
    res = {'name_orig': p['japanese']}
    for k, pn in {'name_rom': p['name'], 'name_rus': p['russian']}.items():
        n = pn.split()
        res[k] = (n[1] + " " if len(n) > 1 else "") + n[0]
    return res


# def studios(_studios: list[dict[str, str | int | bool | None] | None]) -> list[str] | None:
#     """
#     Форматирование списка студий из SH.
#     :param _studios: Список словарей студий из SH.
#     :return: Форматированный список студий.
#     """
#     return [s['name'] for s in _studios]


def directors(aid: int) -> list[dict[str, str]] | None:  # anime: dict[str, str]; aid = anime['id']
    """
    Извлечение режиссёров из БД SH.
    :param aid: ID anime в БД SH.
    :return: Список словарей режиссёров в SH. None — если нет информации о режиссёрах.
    """
    roles = api.animes(aid).roles.GET()
    d = []
    for r in roles:
        if not r['character'] and "Director" in r['roles']:
            d.append(person(r['person']['id']))
    if len(d):
        return d


# def genres(_genres: list[dict[str, str | int] | None]) -> list[str] | None:
#     """
#     Форматирование списка жанров из SH.
#     :param _genres: Список словарей жанров по anime в SH.
#     :return: Форматированный список жанров.
#     """
#     return [GENRES_SH[g['name']] for g in _genres if g['name'] not in IGNORED_GENRES]


# def poster(anime: dict[str, str | int | dict[str, str] | list[str | dict[str, int | str] | None] | None] | None
#            ) -> str | None:
#     """
#     Извлечение URL постера из SH.
#     :param anime: Словарь данных по anime в SH.
#     :return: URL постера в SH.
#     """
#     return SH + anime['image']['original']


def _anime_id(id_: int, _res: str) -> int | None:
    """
    Извлечение ID anime во внешнем ресурсе по ссылке в SH.
    :param id_: ID anime в БД SH.
    :return: ID anime во внешнем ресурсе, если найдена ссылка в SH. Иначе — None.
    """
    global external_links
    if not external_links:
        external_links = api.animes(id_).external_links.GET()
    for el in external_links:
        if el['kind'] == _res:
            return int(el['url'][el['url'].find("?id=") + 4:])


# def wa_anime_id(id_: int) -> int | None:
#     """
#     Извлечение ID anime в WA по ссылке в SH.
#     :param id_: ID anime в БД SH.
#     :return: ID anime в WA, если найдена ссылка в SH. Иначе — None.
#     """
#     return _anime_id(id_, "world_art")


def ann_anime_id(id_: int) -> int | None:
    """
    Извлечение ID anime в ANN по ссылке в SH.
    :param id_: ID anime в БД SH.
    :return: ID anime в ANN, если найдена ссылка в SH. Иначе — None.
    """
    return _anime_id(id_, "anime_news_network")


def extraction_anime(anime: dict[str, str | int | dict[str, str] | list[str | dict[str, int | str] | None] | None] |
                            None) -> dict[str, str | int | list[str] | list[dict[str, str]] | None]:
    """
    Извлечение anime из SH.
    :param anime: Словарь данных по anime в SH.
    :return: Итоговый словарь данных по anime в SH.
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
        'wa': int,
        'ann': int
    }
    """
    print("- sh.extraction_anime(anime):", end=" ")
    result = {
        'name_orig': anime['japanese'][0],
        'name_rom': anime['name'],
        'name_eng': anime['english'][0],
        'name_rus': anime['russian'],
        'format': FORM_SH_WA[anime['kind']],
        'number_of_episodes': anime['episodes'],
        'duration': hours_minutes(anime['duration']),
        'date_of_premiere': anime['aired_on'],
        'studio': [s['name'] for s in anime['studios']],
        'director': directors(anime['id']),
        'genre': [GENRES_SH[g['name']] for g in anime['genres'] if g['name'] not in IGNORED_GENRES],
        'notes': "",
        'poster': SH + anime['image']['original'],
        'wa': _anime_id(anime['id'], "world_art"),
        'ann': _anime_id(anime['id'], "anime_news_network")
    }
    print(result['name_rom'])
    return result
