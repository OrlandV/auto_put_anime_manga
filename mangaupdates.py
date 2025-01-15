"""
Поиск страниц на MangaUpdates и их обработка.
"""
import json
from time import sleep
import requests
from PIL import Image
from urllib.request import urlopen

from constants import *
import db
from decode_name import normal_name


def genres_id(data: json.JSONEncoder, oam: str) -> list[int]:
    """
    Извлечение жанров из MangaUpdates.
    :param data: Данные по манге с MangaUpdates в JSON-формате.
    :param oam: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID жанров в БД.
    """
    result = []
    new_genres = {}
    for genre in data['genres']:
        if genre['genre'] not in IGNORED_GENRES_MU:
            if genre['genre'] in GENRES_MU:
                pos2 = oam.find(f'">{GENRES_MU[genre['genre']]}</option>')
                pos1 = oam.find('="', pos2 - 5) + 2
                result.append(int(oam[pos1:pos2]))
            else:
                print('Новый жанр в MangaUpdates!', genre['genre'])
                add = input('Добавить жанр? Y/N: ')
                if add == 'Y' or add == 'y':
                    new_genre = input('Наименование жанра на русском: ')
                    result.append(db.put(f'{OAM}frmAddGenre.php', {'name_': new_genre}))
                    new_genres[genre['genre']] = new_genre
    if len(new_genres):
        with open('new_genres.json', 'a', encoding='utf8') as file:
            json.dump(new_genres, file, indent=4)
        print('Перенесите новые жанры в «config.py» из «new_genres.json».')
    return result


def manga_json(mu_id: int) -> json.JSONEncoder:
    """
    Манга в MangaUpdates.
    :param mu_id: ID манги в MangaUpdates.
    :return: Данные по манге с MangaUpdates в JSON-формате.
    """
    sleep(1)
    return requests.get(f'{AMUS}{mu_id}').json()


def related_manga(mu_json: json.JSONEncoder) -> list[dict]:
    """
    Поиск по ID манги в MangaUpdates, извлечение ID связанной манги и пометка их для обработки.
    :param mu_json: Данные по манге с MangaUpdates в JSON-формате.
    :return: Список словарей [dict(id=mu_id: int, name=name: str, add=добавлять?: bool)].
    """
    result = []
    for rs in mu_json['related_series']:
        result.append({'id': rs['related_series_id'], 'name': rs['related_series_name'], 'add': True})
    return result


def related_manga_id(mu_id: int) -> list[dict]:
    """
    Поиск по ID манги в MangaUpdates, извлечение ID связанной манги и пометка их для обработки.
    :param mu_id: ID манги в MangaUpdates.
    :return: Список словарей [dict(id=mu_id: int, name=name: str, add=добавлять?: bool)].
    """
    data = manga_json(mu_id)
    return related_manga(data)


def related_manga_title(title: str) -> list[dict]:
    """
    Поиск по наименованию манги в MangaUpdates, извлечение ID связанной манги и пометка их для обработки.
    :param title: Наименование манги.
    :return: Список словарей [dict(id=mu_id: int, name=name: str, add=добавлять?: bool)].
    """
    title = normal_name(title)
    sleep(1)
    data = requests.post(AMUS + 'search', {'search': title}).json()
    for res in data['results']:
        if title == normal_name(res['hit_title']):
            mu_id = res['record']['series_id']
            break
    else:
        return []
    return related_manga_id(mu_id)


def authors_of_manga_id(mu_json: json.JSONEncoder, oam: str) -> list[int] | bool:
    """
    Поиск ID соответствующих авторов манги из MangaUpdates в БД.
    :param mu_json: Данные по манге с MangaUpdates в JSON-формате.
    :param oam: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID авторов манги в БД, если найдены. Иначе — False.
    """
    authors = []
    for author in mu_json['authors']:
        if author['type'] == 'Author':
            sleep(1)
            author_json = requests.get(f'{AMUA}{author['author_id']}').json()
            authors.append({'name_orig': author_json['actualname'],
                            'name_rom': author_json['name'].lower().title(),
                            'exist': False})
    return db.authors_of_manga_id(authors, oam)


# def put_publication(publication: dict) -> int:
#     """
#     Добавление издания в БД из MangaUpdates и возврат ID.
#     :param publication: Издание.
#     :return: ID издания в БД.
#     """
#     return db.put_publication(publication)


def publications_id(mu_json: json.JSONEncoder, oam: str) -> list[int] | bool:
    """
    Поиск ID соответствующих изданий манги из MangaUpdates в БД.
    :param mu_json: Данные по манге с MangaUpdates в JSON-формате.
    :param oam: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID изданий манги в БД, если найдены. Иначе — False.
    """
    if 'publications' not in mu_json:
        return False
    publications = []
    for publication in mu_json['publications']:
        publications.append({'name': publication['publication_name'],
                             'publishing': publication['publisher_name'],
                             'exist': False})
    if not len(publications):
        for publisher in mu_json['publishers']:
            publications.append({'name': f'? ({publisher['publisher_name']})',
                                 'publishing': publisher['publisher_name'],
                                 'type': 2,
                                 'exist': False})
    return db.publications_id(oam, publications, db.put_publication)


def select_title(mu_json: json.JSONEncoder, lang: str) -> str:
    """
    Выбор наименования манги через обращение к пользователю.
    :param mu_json: Данные по манге с MangaUpdates в JSON-формате.
    :param lang: Язык наименования: "orig", "eng", "rus".
    :return: Наименование манги.
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
    text = '\n0. *** Подходящего варианта нет ***'
    for i, title in enumerate(mu_json['associated']):
        titles.append(title['title'])
        text += f'\n{i + 1}. {title['title']}'
    print(f'Выберите {lang} наименование манги «{mu_json['title']}»:{text}')
    while True:
        num = input('Укажите номер: ')
        if num.isdigit():
            num = int(num)
            break
        print('Ошибка! Требуется ввести целое число.')
    if not num:
        return ''
    return titles[num - 1]


def volumes(mu_json: json.JSONEncoder) -> int:
    """
    Количество томов.
    :param mu_json: Данные по манге с MangaUpdates в JSON-формате.
    :return: Количество томов или количество глав (отрицательное число).
    """
    p = mu_json['status'].find(' ')
    n = int(mu_json['status'][:p])
    if mu_json['status'][p + 1:p + 2] == 'V':
        return n
    return -n


def poster(mu_json: json.JSONEncoder, mid: int, name: str) -> None:
    """
    Поиск, загрузка и сохранение постера манги с сервера MangaUpdates в виде миниатюрной картинки для своей БД.
    :param mu_json: Данные по манге с MangaUpdates в JSON-формате.
    :param mid: ID в БД (возвращённое db.put).
    :param name: Наименование.
    """
    try:
        url = mu_json['image']['url']['thumb']
    except Exception:
        with open(f'{PATH}m/report.log', 'a', encoding='utf8') as file:
            file.write(f'{mid},"{name}","Нет постера."')
        return
    else:
        img = Image.open(urlopen(url))
        img.thumbnail((100, 100))
        img.save(f'{PATH}m/{mid}.jpg')
