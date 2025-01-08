"""
Интерфейс БД.
"""
import requests
import re

from config import *
import world_art as wa
from decode_name import decode_name


def frequency(publishing: str, publication: str) -> str:
    """
    Коррекция наименования издания, сверяя по World Art.
    :param publishing: Наименование издательства.
    :param publication: Наименование издания.
    :return: Скорректированное наименование издания.
    """
    if wa.valid_publication(publishing, publication):
        return publication
    for key in FREQUENCY_WP.keys():
        if key in publication:
            publication_ = publication.replace(key, FREQUENCY_WP[key])
            if wa.valid_publication(publishing, publication_):
                return publication_
    return publication


def put(url: str, data: dict) -> int:
    """
    Добавление записи в БД и возврат ID.
    :param url: URL для request.
    :param data: Данные для метода post (кроме кнопки отправки формы, которая добавляется в данной функции).
    :return: ID в БД.
    """
    data['ok'] = 'OK'
    r = requests.post(url, data, cookies=COOKIES_O)
    r = requests.get(url, {'sort': 'identd'}, cookies=COOKIES_O).text
    pos1 = r.find('<th></th>')
    pos1 = r.find('<td class="cnt">', pos1) + 16
    pos2 = r.find('</td>', pos1)
    return int(r[pos1:pos2])


def put_publication(data: dict) -> int:
    """
    Добавление издания в БД и возврата ID.
    :param data: Словарь данных для формы добавления издания.
    :return: ID издания в БД.
    """
    data_ = {'name_': data['name'], 'putyp': data['type']}
    url = f'{OAM}frmAddPublication.php'
    op = requests.get(url, cookies=COOKIES_O).text
    pos1 = op.find('<select name="mapbs"')
    pos2 = op.find('</select>', pos1)
    pos2 = op.find(f'">{data['publishing']}</option>', pos1, pos2)
    if pos2 != -1:
        pos1 = op.find('value="', pos2 - 15, pos2) + 7
        data_['mapbs'] = int(op[pos1:pos2])
    else:  # Добавление издательства в БД и получение ID.
        data_['mapbs'] = put(f'{OAM}frmAddPublishing.php', {'name_': data['publishing']})
    return put(url, data_)


def publications_id(oam: str, publications: list[dict], put_publication_site) -> list[int]:
    """
    Поиск ID соответствующих изданий в БД.
    :param oam: Страница веб-приложения интерфейса БД (HTML-код).
    :param publications: Список словарей изданий.
    :param put_publication_site: Функция добавления издания в БД для соответствующего сайта.
    :return: Список ID изданий в БД.
    """
    pos1 = oam.find('<select name="mapbc[]"')
    pos2 = oam.find('</select>', pos1)
    result = []
    for i in range(len(publications)):
        if 'publishing' in publications[i]:
            publications[i]['name'] = frequency(publications[i]['publishing'], publications[i]['name'])
        pattern = (r'<option value="(.*?)">(.*?) \(Журнал\. .*?\)</option>' if 'type' not in publications[i] or
                                                                               publications[i]['type'] == 1 else
                   r'<option value="(.*?)">(.*?) \(Книга\. .*?\)</option>' if publications[i]['type'] == 2 else
                   r'<option value="(.*?)">(.*?) \(Веб\. .*?\)</option>')
        o_publications = re.findall(pattern, oam[pos1:pos2])
        for publication in o_publications:
            if publication[1] == publications[i]['name']:
                result.append(int(publication[0]))
                publications[i]['exist'] = True
                break
    if len(result) < len(publications):
        for publication in publications:
            if not publication['exist']:
                result.append(put_publication_site(publication))
    return result


def put_people(people: dict, type_people: str) -> int:
    """
    Добавление персоны в БД и возврата ID.
    :param people: Словарь имён.
    :param type_people: Тип персоны (специализация).
    :return: ID персоны в БД.
    """
    return put(f'{OAM}frmAdd{type_people}.php',
               {'naori': decode_name(people['name_orig']), 'narom': people['name_rom']})


def authors_of_manga_id(authors: list[dict], oam: str) -> list[int] | bool:
    """
    Поиск ID соответствующих авторов манги в БД.
    :param authors: Список авторов.
    :param oam: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID авторов манги в БД, если найдены. Иначе — False.
    """
    if not len(authors):
        return False
    pos1 = oam.find('<select name="maaum[]"')
    pos2 = oam.find('</select>', pos1)
    o_authors = re.findall(r'<option value="(.*?)">(.*?) / (.*?) / .*?</option>', oam[pos1:pos2])
    result = []
    for i in range(len(authors)):
        for author in o_authors:
            if (author[2] == authors[i]['name_rom'] or
                    author[1].replace(' ', '') == authors[i]['name_orig'].replace(' ', '')):
                result.append(int(author[0]))
                authors[i]['exist'] = True
                break
    if len(result) < len(authors):
        for author in authors:
            if not author['exist']:
                result.append(put_people(author, 'AuthorOfManga'))
    return result


def select_genres(oam: str, title: str) -> list:
    """
    Выбор пользователем жанров.
    :param oam: Страница веб-приложения интерфейса БД (HTML-код).
    :param title: Наименование anime или манги.
    :return: Список ID жанров в БД.
    """
    pos1 = oam.find('<select name="genre[]"')
    pos2 = oam.find('</select>', pos1)
    o_genres = re.findall(r'<option value="(.*?)">(.*?)</option>', oam[pos1:pos2])
    text = f'Для «{title}» не определены жанры. Выберите жанры из списка и укажите их номера через пробел.'
    for genre in o_genres:
        text += f'\n{genre[0]}. {genre[1]}'
    print(text)
    while True:
        numbers = input('Ваш выбор: ')
        numbers = numbers.strip().split(' ')
        try:
            return list(map(int, numbers))
        except ValueError:
            print('Ошибка! Требуется ввести целые числа через пробел.')
