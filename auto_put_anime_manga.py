import requests
from time import sleep
import re
from datetime import time
import xml.etree.ElementTree as et
from PIL import Image
from urllib.request import urlopen
from config import *
from input import *

WA = 'http://www.world-art.ru/'
A = 'animation'
WAA = WA + A + '/'
WAAA = WAA + A + '.php'
M = 'manga'
WAAM = WAA + M + '.php'
ANN = 'http://www.animenewsnetwork.com/'
ANNE = ANN + 'encyclopedia/'
CANNE = 'https://cdn.animenewsnetwork.com/encyclopedia/'


def points_codes(text: str) -> str:
    """
    Функция замены не буквенно-цифровых символов их кодами в формате «&#1;»–«&#127;».
    :param text: Текст.
    """
    text = text.replace('—', '-').replace('…', '...').replace('½', '1/2')
    points = (list(range(1, 32)) + list(range(33, 36)) + [37] + list(range(40, 48)) +
              list(range(58, 65)) + list(range(91, 97)) + list(range(123, 128)))
    text2 = ''
    for i in range(len(text)):
        p = ord(text[i])
        if p in points:
            text2 += f'&#{p};'
        else:
            text2 += text[i]
    return text2


def search_anime_in_wa(search: str, form: str, year: int) -> str | None:
    """
    Функция поиска страницы anime на World Art.
    :param search: Искомое наименование.
    :param form: Формат.
    :param year: Год.
    :return: Страница (HTML-код), если найдена. Иначе — None.
    """
    search_ = points_codes(search)
    data = requests.get(WA + 'search.php', cookies=COOKIES_WA,
                        params={'public_search': search_, 'global_sector': A}).text
    aid = 0
    if data.find("<meta http-equiv='Refresh'") != -1:
        aid = int(data[data.find('?id=') + 4:-2])
    else:
        posa = 0
        ls = len(search_)
        wb = False
        str_sub = f'<a href = "{A}/{A}.php?id='
        lss = len(str_sub)
        while True:
            posa = data.find(str_sub, posa) + lss
            if posa == lss - 1:
                break
            pos = posa
            postd = data.find('</td>', pos)
            while True:
                pos = data.find(search_, pos, postd)
                if pos == -1:
                    break
                pos1 = pos + ls
                if (data[pos1:pos1 + 7] == '&nbsp;(' or data[pos1:pos1 + 4] == '<br>') and data[pos - 1:pos] == '>':
                    posf1 = data.find(', Япония, ', posa) + 10
                    posf2 = data.find(',', posf1)
                    if posf2 == -1:
                        posf2 = data.find(')', posf1)
                    if form in data[posf1:posf2] and str(year) in data[posf1 - 14:posf1 - 10]:
                        wb = True
                        break
                pos = pos1
            if wb:
                break
    if aid == 0 and posa in (33, 37):
        with open('report.csv', 'a', encoding='utf8') as file:
            file.write(
                f'"{search}","Ошибка. Возможно искомое наименование отредактировано и теперь не совпадает."\n'
            )
        return None
    elif aid == 0:
        aid = int(data[posa:data.find('" ', posa)])
    sleep(1)
    return requests.get(WAAA, {'id': aid}, cookies=COOKIES_WA).text


def search_manga_in_wa_anime_page(page: str) -> str | None:
    """
    Функция поиска манги, связанной с anime на World Art.
    :param page: Страница anime на World Art (HTML-код, возвращённый search_anime_in_wa).
    :return: Страница манги на World Art (HTML-код).
    """
    pos = page.find('<b>Снято по манге</b>')
    if pos == -1:
        return None
    url = WAAM
    pos = page.find(url, pos) + 47
    mid = int(page[pos:page.find('" ', pos)])
    sleep(1)
    return requests.get(url, {'id': mid}, cookies=COOKIES_WA).text


def wa_manga_pages(page: str) -> list:
    """
    Функция поиска продолжений манги на World Art и формирования списка страниц.
    :param page: Страница манги на World Art (HTML-код, возвращённый search_manga_in_wa_anime_page).
    :return: Список страниц.
    """
    pos1 = page.find("<link rel='canonical' href='") + 75
    mid = int(page[pos1:page.find("' />", pos1)])
    pos1 = page.find('<font size=2 color=#000000>Эта серия состоит из</font>', pos1)
    if pos1 == -1:
        return [page]
    i = 1
    url = f'{M}.php'
    res = []
    while True:
        pos1 = page.find(f'<td Valign=top> <b>#{i}&nbsp;</b></td>', pos1)
        if pos1 == -1:
            break
        if i == 1:
            pos2 = page.find('</table', pos1)
        pos1 = page.find(f'<a href = "{url}?id=', pos1, pos2) + 24
        nid = int(page[pos1:page.find('" ', pos1, pos2)])
        # if nid in (mid, ):
        #     i += 1
        #     continue
        if nid == mid:
            res.append(page)
        else:
            sleep(1)
            res.append(requests.get(WAAM, {'id': nid}, cookies=COOKIES_WA).text)
        i += 1
    if len(res) == 0:
        return [page]
    return res


def manga_in_ann(page: str) -> str | bool:
    """
    Страница манги в ANN по ID из World Art.
    :param page: Страница манги на World Art (HTML-код).
    :return: XML-страница манги на ANN, если есть ссылка. Иначе False.
    """
    pos1 = page.find('<b>Сайты</b>')
    pos2 = page.find('</table>', pos1)
    url = f'{ANNE}{M}.php'
    pos1 = page.find(url, pos1, pos2) + 58
    if pos1 == 57:
        return False
    mid = int(page[pos1:page.find("' ", pos1, pos2)])
    sleep(1)
    # return requests.get(url, {'id': mid}, cookies=COOKIES_WA).text
    return requests.get(f'{CANNE}api.xml', {M: mid}).text


def number_of_volumes_ann(ann_xml: str) -> int:
    """
    Функция поиска количества томов манги на ANN.
    :param ann_xml: XML-страница манги на ANN.
    :return: Количество томов манги.
    """
    # root = et.fromstring(ann_xml)
    # for info in root[0].findall('info'):
    #     if info.get('type') == 'Number of tankoubon':
    #         return int(info.text)
    pos = ann_xml.find('Number of tankoubon') + 21
    return int(ann_xml[pos:ann_xml.find('<', pos)])


def manga_in_wp(page: str) -> str | bool:
    """
    Страница манги в Wikipedia по ссылке из World Art.
    :param page: Страница манги на World Art (HTML-код).
    :return:
    """
    pos1 = page.find('<b>Вики</b>')
    pos2 = page.find('</table>', pos1)
    pos1 = page.find('https://en.wikipedia.org/', pos1, pos2)
    if pos1 == -1:
        return False
    url = page[pos1:page.find('" ', pos1, pos2)]
    sleep(1)
    return requests.get(url).text


def number_of_volumes_wp(page: str) -> int:
    """
    Функция поиска количества томов манги на Wikipedia.
    :param page: Страница манги на Wikipedia (HTML-код).
    :return: Количество томов манги.
    """
    pos = page.find('<th scope="row" class="infobox-label">Volumes</th><td class="infobox-data">') + 75
    if pos == -1:
        return 0
    return int(page[pos:page.find('</td>', pos)])


def put_in_db(url: str, data: dict) -> int:
    """
    Функция добавления записи в БД и возврата ID.
    :param url: URL для request.
    :param data: Данные для метода post.
    :return: ID в БД.
    """
    r = requests.post(url, data, cookies=COOKIES_O)
    r = requests.get(url, {'sort': 'identd'}, cookies=COOKIES_O).text
    pos1 = r.find('<th></th>')
    pos1 = r.find('<td class="cnt">', pos1) + 16
    pos2 = r.find('</td>', pos1)
    return int(r[pos1:pos2])


def put_people(pid: int, type_people: str) -> int:
    """
    Функция добавления персоны в БД и возврата ID.
    :param pid: ID персоны в WA.
    :param type_people: Тип персоны (специализация).
    :return: ID персоны в БД.
    """
    sleep(1)
    page = requests.get(f'{WA}people.php', {'id': pid}, cookies=COOKIES_WA).text
    pos1 = page.find('<font size=5>') + 13
    pos2 = page.find('</font>', pos1)
    data = {'ok': 'OK', 'narus': page[pos1:pos2]}
    pos1 = page.find('<b>Имя по-английски</b>', pos2)
    pos1 = page.find("class='review'>", pos1) + 15
    pos2 = page.find('</td>', pos1)
    data['narom'] = page[pos1:pos2]
    pos1 = page.find('<b>Оригинальное имя</b>', pos2)
    pos1 = page.find("class='review'>", pos1) + 15
    pos2 = page.find('</td>', pos1)
    data['naori'] = decode_name(page[pos1:pos2])
    url = f'{OAM}frmAdd{type_people}.php'
    return put_in_db(url, data)


def wa_authors_of_manga_id(page: str, oam: str) -> list:
    """
    Функция поиска ID соответствующих авторов манги из WA в БД.
    :param page: World Art страница (HTML-код).
    :param oam: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID авторов манги в БД.
    """
    pos1 = page.find('<b>Авторы</b>')
    pos2 = page.find('</table>', pos1)
    wa_authors = []
    i = 0
    while True:
        pos1 = page.find('/people.php?id=', pos1, pos2) + 15
        if pos1 == 14:
            break
        pos = page.find(" class='review'>", pos1, pos2) - 1
        wa_authors.append({'id': int(page[pos1:pos]), 'exist': False})
        pos1 = pos + 17
        wa_authors[i]['name'] = page[pos1:page.find('</a>', pos1, pos2)]
        i += 1
    pos1 = oam.find('<select name="maaum[]"')
    pos2 = oam.find('</select>', pos1)
    o_authors = re.findall(r'<option value="(.*?)">.*? / .*? / (.*?)</option>', oam[pos1:pos2])
    result = []
    for i in range(len(wa_authors)):
        for author in o_authors:
            if author[1] == wa_authors[i]['name']:
                result.append(int(author[0]))
                wa_authors[i]['exist'] = True
                break
    if len(result) < len(wa_authors):
        for wa_author in wa_authors:
            if not wa_author['exist']:
                result.append(put_people(wa_author['id'], 'AuthorOfManga'))
    return result


def put_publication(pid: int, name: str) -> int:
    """
    Функция добавления издания в БД и возврата ID.
    :param pid: ID издания в WA.
    :param name: Наименование издания.
    :return: ID издания в БД.
    """
    data = {'ok': 'OK', 'name_': name, 'putyp': 1}
    url = f'{WA}company.php'
    sleep(1)
    page = requests.get(url, {'id': pid}, cookies=COOKIES_WA).text
    pos1 = page.find(f'<b>{name}</b>')
    pos2 = page.find('<b>Сериализация</b>', pos1)
    # pos1 = page.find(url, pos1, pos2)
    pos1 = page.find('company.php', pos1, pos2)
    pos1 = page.find("class='review'>", pos1, pos2) + 15
    publishing = page[pos1:page.find('</a>', pos1, pos2)]
    url = f'{OAM}frmAddPublication.php'
    op = requests.get(url, cookies=COOKIES_O).text
    pos1 = op.find('<select name="mapbs"')
    pos2 = op.find('</select>', pos1)
    # o_publishing = re.findall(r'<option value="(.*?)">(.*?)</option>', op[pos1:pos2])
    pos2 = op.find(f'">{publishing}</option>', pos1, pos2)
    if pos2 != -1:
        pos1 = op.find('value="', pos2 - 15, pos2) + 7
        data['mapbs'] = int(op[pos1:pos2])
    else:
        data['mapbs'] = put_in_db(f'{OAM}frmAddPublishing.php', {'name_': publishing, 'ok': 'OK'})
    return put_in_db(url, data)


def wa_publications_id(page: str, oam: str) -> list:
    """
    Функция поиска ID соответствующих изданий из WA в БД.
    :param page: World Art страница (HTML-код).
    :param oam: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID изданий в БД.
    """
    pos1 = page.find('<b>Сериализация</b>')
    pose = page.find('</table>', pos1)
    wa_publications = []
    i = 0
    while True:
        pos1 = page.find('/company.php?id=', pos1, pose) + 16
        if pos1 == 15:
            break
        pos2 = page.find("' class='review'>", pos1, pose)
        wa_publications.append({'id': int(page[pos1:pos2]), 'exist': False})
        pos1 = pos2 + 17
        wa_publications[i]['name'] = page[pos1:page.find('</a>', pos1)]
        i += 1
    pos1 = oam.find('<select name="mapbc[]"')
    pos2 = oam.find('</select>', pos1)
    o_publications = re.findall(r'<option value="(.*?)">(.*?) \(Журнал\. .*?\)</option>', oam[pos1:pos2])
    result = []
    for i in range(len(wa_publications)):
        for publication in o_publications:
            if publication[1] == wa_publications[i]['name']:
                result.append(int(publication[0]))
                wa_publications[i]['exist'] = True
                break
    if len(result) < len(wa_publications):
        for wa_publication in wa_publications:
            if not wa_publication['exist']:
                result.append(put_publication(wa_publication['id'], wa_publication['name']))
    return result


def wa_genres_id(wa_page: str, o_page: str) -> list:
    """
    Функция поиска ID соответствующих жанров из WA в БД.
    :param wa_page: World Art страница (HTML-код).
    :param o_page: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID жанров в БД.
    """
    # wa_genres = re.findall(
    #     r"<a href='http://www\.world-art\.ru/animation/list\.php\?public_genre=\d+' class='review'>(.*?)</a>",
    #     wa_page
    # )
    pos1 = wa_page.find('<b>Жанр</b>')
    pos2 = wa_page.find('</table>', pos1)
    pos1 = wa_page.find("class='review'>", pos1, pos2) + 15
    wa_genres = []
    while pos1 > 14:
        wa_genres.append(wa_page[pos1:wa_page.find('</a>', pos1, pos2)])
        pos1 = wa_page.find("class='review'>", pos1, pos2) + 15
    for genre in ('сэйнэн',):  # Планируется добавить жанры в кортеж.
        if genre in wa_genres:
            wa_genres.remove(genre)
    result = []
    for genre in wa_genres:
        pos2 = o_page.find(f'">{genre}</option>')
        pos1 = o_page.find('="', pos2 - 5) + 2
        result.append(int(o_page[pos1:pos2]))
    return result


def decode_name(name: str) -> str:
    return re.sub(r'&#(\d+);', lambda m: chr(int(m[1])), name)


def wa_name_orig(wa_page: str, am=0) -> str:
    """
    Функция извлечения оригинального наименования из WA.
    :param wa_page: World Art страница (HTML-код).
    :param am: Переключатель: anime/манга (0/1).
    :return: Оригинальное наименование.
    """
    pos1 = wa_page.find(f'<b>Названи{'я' if am else 'е'} (кандзи)</b>')
    if pos1 == -1:
        pos1 = wa_page.find(f'<b>Названия (прочие)</b>')
    if pos1 != -1:
        pos1 = wa_page.find('Valign=top>', pos1) + 11
        pos2 = wa_page.find('</td>', pos1)
        return decode_name(wa_page[pos1:pos2])
    return wa_name_rus(wa_page)


def wa_name_rom(wa_page: str, am=0) -> str:
    """
    Функция извлечения наименования на ромадзи из WA.
    :param wa_page: World Art страница (HTML-код).
    :param am: Переключатель: anime/манга (0/1).
    :return: Наименование на ромадзи.
    """
    pos1 = wa_page.find(f'<b>Названи{'я (яп.' if am else 'е (ромадзи'})</b>')
    if pos1 == -1:
        pos1 = wa_page.find('<font size=5>') + 13
        pos2 = wa_page.find('</font>', pos1)
    else:
        pos1 = wa_page.find('Valign=top>', pos1) + 11
        pos2 = wa_page.find('</td>', pos1)
    return decode_name(wa_page[pos1:pos2]).replace(' - ', ' — ').replace('...', '…')


def wa_name_eng(wa_page: str, am=0) -> str:
    """
    Функция извлечения наименования на английском из WA.
    :param wa_page: World Art страница (HTML-код).
    :param am: Переключатель: anime/манга (0/1).
    :return: Наименование на английском.
    """
    pos1 = wa_page.find(f'<b>Названи{'я' if am else 'е'} (англ.)</b>')
    if pos1 == -1:
        return ''
    pos1 = wa_page.find('Valign=top>', pos1) + 11
    pos2 = wa_page.find('</td>', pos1)
    return decode_name(wa_page[pos1:pos2]).replace(' - ', ' — ').replace('...', '…')


def wa_name_rus(wa_page: str) -> str:
    """
    Функция извлечения наименования на русском из WA.
    :param wa_page: World Art страница (HTML-код).
    :return: Наименование на русском.
    """
    pos1 = wa_page.find('<font size=5>') + 13
    pos2 = wa_page.find('</font>', pos1)
    return decode_name(wa_page[pos1:pos2]).replace(' - ', ' — ').replace('...', '…')


def wa_manga_name_r(wa_name_r, *args) -> str:
    """
    Удаление в названии окончания « (манга)».
    :param wa_name_r: Функция wa_name_rom или wa_name_rus.
    :return: Исправленное название.
    """
    wa_name = wa_name_r(*args)
    return wa_name[:wa_name.find(' (манга)')]


def number_of_chapters(ann_page: str) -> int:
    pass


def wa_date_of_premiere_manga(wa_page: str) -> str:
    """
    Функция поиска даты премьеры (года выпуска) манги на World Art.
    :param wa_page: World Art страница (HTML-код).
    :return: Дата премьеры манги в формате гггг-мм-чч.
    """
    pos1 = wa_page.find('<b>Год выпуска</b>')
    pose = wa_page.find('</table>', pos1)
    pos1 = wa_page.find('Valign=top>', pos1, pose) + 11
    return wa_page[pos1:wa_page.find('</td>', pos1, pose)] + '-12-31'


def extraction_manga_from_wa(wa_page: str) -> dict:
    """
    Функция извлечения данных из страницы (HTML-кода) манги на World Art. Недостающие данные ищутся на ANN.
    :param wa_page: Страница (HTML-код), возвращённый функцией search_manga_in_wa_anime_page.
    :return: Словарь данных.
    """
    if ann_page := manga_in_ann(wa_page):
        nv = number_of_volumes_ann(ann_page)
    elif wp_page := manga_in_wp(wa_page):
        nv = number_of_volumes_wp(wp_page)
    oam = requests.get(f'{OAM}frmAddManga.php', cookies=COOKIES_O).text
    res = {
        'maaum[]': wa_authors_of_manga_id(wa_page, oam),
        'mapbc[]': wa_publications_id(wa_page, oam),
        'genre[]': wa_genres_id(wa_page, oam),
        'amnor': wa_name_orig(wa_page, 1),
        'amnro': wa_manga_name_r(wa_name_rom, wa_page, 1),
        'amnen': wa_name_eng(wa_page, 1),
        'amnru': wa_manga_name_r(wa_name_rus, wa_page),
        'manvo': nv,
        'manch': nv,  # number_of_chapters(ann_page),
        'amdpr': wa_date_of_premiere_manga(wa_page),
        'notes': 'Нет инф-и о кол-ве глав и точной дате премьеры.'
    }
    if res['amnru'] == res['amnro']:
        res['amnru'] = ''
    dk = []
    for k, v in res.items():
        if not isinstance(v, int) and len(v) == 0:
            dk.append(k)
    for k in dk:
        del res[k]
    res['ok'] = 'OK'
    return res


def wa_anime_pages(page: str) -> list:
    """
    Функция поиска продолжений anime на World Art и формирования списка страниц.
    :param page: Страница anime на World Art (HTML-код, возвращённый search_anime_in_wa).
    :return: Список страниц.
    """
    pos1 = page.find("<link rel='canonical' href='") + 79
    aid = int(page[pos1:page.find("' />", pos1)])
    pos1 = page.find('<font size=2>Информация о серии</font>', pos1)
    if pos1 == -1:
        return [page]
    i = 1
    res = []
    while True:
        pos1 = page.find(f'<td Valign=top width=20> <b>#{i}&nbsp;</b></td>', pos1)
        if pos1 == -1:
            break
        if i == 1:
            pos2 = page.find('</table', pos1)
        pos1 = page.find(f'<a href = "{WAAA}?id=', pos1, pos2) + 62
        nid = int(page[pos1:page.find('" ', pos1, pos2)])
        # if nid in (aid, ):
        #     i += 1
        #     continue
        if nid == aid:
            res.append(page)
        else:
            sleep(1)
            res.append(requests.get(WAAA, {'id': nid}, cookies=COOKIES_WA).text)
        i += 1
    if len(res) == 0:
        return [page]
    return res


def wa_format_id(wa_page: str, o_page: str) -> int:
    """
    Функция поиска ID соответствующего формата из WA в БД.
    :param wa_page: World Art страница (HTML-код).
    :param o_page: Страница веб-приложения интерфейса БД (HTML-код).
    :return: ID формата в БД.
    """
    pos1 = wa_page.find('<b>Тип</b>') + 63
    pos2 = wa_page.find('</table>', pos1)
    pos = wa_page.find(' (', pos1, pos2)
    if pos == -1:
        pos = wa_page.find(',', pos1, pos2)
    result = wa_page[pos1:pos]
    pos2 = o_page.find(f'">{result}</option>')
    # if pos2 == -1:
    #     Добавить.
    #     r = requests.post(f'{OAM}frmAddFormat.php', data={'name_f': result}, cookies=COOKIES_O)
    #     Записать ID.
    #     pos2 = o_page.find(f'">{result}</option>')
    pos1 = o_page.find('="', pos2 - 4) + 2
    return int(o_page[pos1:pos2])


def wa_studios_id(wa_page: str, o_page: str) -> list:
    """
    Функция поиска ID соответствующих студий из WA в БД.
    :param wa_page: World Art страница (HTML-код).
    :param o_page: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID студий в БД.
    """
    url = f'{WAA}{A}_full_production.php'
    pos1 = wa_page.find('<b>Основное</b>') + 15
    pos1 = wa_page.find(url, pos1) + 67
    if pos1 == 66:
        return [1]
    pos2 = wa_page.find('" >компании', pos1)
    if pos2 == -1:
        return [1]
    aid = wa_page[pos1:pos2]
    sleep(1)
    data = requests.get(url, {'id': aid}, cookies=COOKIES_WA).text
    pos1 = data.find('<b>Производство:</b>')
    if pos1 == -1:
        return [1]
    pos2 = data.find('</table>', pos1)
    pos1 = data.find("class='estimation'>", pos1, pos2) + 19
    studios = []
    while pos1 > 18:
        studios.append(decode_name(data[pos1:data.find('</a>', pos1, pos2)]))
        pos1 = data.find("class='estimation'>", pos1, pos2) + 19
    result = []
    for studio in studios:
        pos2 = o_page.lower().find(f'">{studio.lower()}</option>')
        if pos2 != -1:
            pos1 = o_page.find('="', pos2 - 5) + 2
            result.append(int(o_page[pos1:pos2]))
        else:
            result.append(put_in_db(f'{OAM}frmAddStudio.php', {'name_s': studio, 'ok': 'OK'}))
    return result


def wa_directors_id(wa_page: str, o_page: str) -> list:
    """
    Функция поиска ID соответствующих режиссёров из WA в БД.
    :param wa_page: World Art страница (HTML-код).
    :param o_page: Страница веб-приложения интерфейса БД (HTML-код).
    :return: Список ID режиссёров в БД.
    """
    url = f'{WAA}{A}_full_cast.php'
    pos1 = wa_page.find('<b>Основное</b>') + 15
    pos1 = wa_page.find(url, pos1) + 61
    if pos1 == 60:
        return [1]
    pos2 = wa_page.find('" >авторы', pos1)
    if pos2 == -1:
        return [1]
    aid = wa_page[pos1:pos2]
    sleep(1)
    data = requests.get(url, {'id': aid}, cookies=COOKIES_WA).text
    pos1 = data.find('<b>Режиссер:</b>')
    pos2 = data.find('</table>', pos1)
    ex = data.find('режиссер эпизода/сегмента')
    if ex == -1:
        ex = pos2
    wa_directors = []
    i = 0
    while True:
        pos1 = data.find('people.php?id=', pos1, pos2) + 14
        tr = data.find('<tr>', pos1, pos2)
        if tr == -1:
            tr = pos2
        if pos1 == 13 or tr > ex:
            break
        wa_directors.append({'id': int(data[pos1:data.find('" ', pos1, pos2)]), 'exist': False})
        pos1 = data.find("class='estimation'>", pos1, pos2) + 19
        wa_directors[i]['name'] = data[pos1:data.find('</a>', pos1, pos2)]
        i += 1
    pos1 = o_page.find('<select name="andir[]"')
    pos2 = o_page.find('</select>', pos1)
    o_directors = re.findall(r'<option value="(.*?)">.*? / .*? / (.*?)</option>', o_page[pos1:pos2])
    result = []
    for i in range(len(wa_directors)):
        for o_director in o_directors:
            if o_director[1] == wa_directors[i]['name']:
                result.append(int(o_director[0]))
                wa_directors[i]['exist'] = True
                break
    if len(result) < len(wa_directors):
        for wa_director in wa_directors:
            if not wa_director['exist']:
                result.append(put_people(wa_director['id'], 'Director'))
    return result


def wa_number_of_episodes(wa_page: str) -> int:
    """
    Функция извлечения количества эпизодов из WA.
    :param wa_page: World Art страница (HTML-код).
    :return: Количество эпизодов.
    """
    pos1 = wa_page.find('<b>Тип</b>')
    pos2 = wa_page.find('</table>', pos1)
    pos1 = wa_page.find(' (', pos1, pos2) + 2
    if pos1 == 1:
        return 1
    pos2 = wa_page.find(' эп.', pos1, pos2)
    return int(wa_page[pos1:pos2])


def wa_duration(wa_page: str):
    """
    Функция извлечения продолжительности эпизода из WA.
    :param wa_page: World Art страница (HTML-код).
    :return: Продолжительность эпизода в формате чч:мм.
    """
    pos1 = wa_page.find('<b>Тип</b>')
    pos2 = wa_page.find('</table>', pos1)
    pos = wa_page.find('), ', pos1, pos2) + 3
    if pos == 2:
        pos = wa_page.find(', ', pos1, pos2) + 2
    pos2 = wa_page.find(' мин.', pos1, pos2)
    m = int(wa_page[pos:pos2])
    h = 0
    if m > 60:
        h = m // 60
        m = m - 60 * h
    t = time(h, m)
    return t.isoformat('minutes')


def wa_date_of_premiere_anime(wa_page: str) -> str:
    """
    Функция извлечения даты премьеры из WA.
    :param wa_page: World Art страница (HTML-код).
    :return: Дата премьеры в формате гггг-мм-дд.
    """
    pos = wa_page.find('<b>Выпуск</b>')
    if pos == -1:
        pos = wa_page.find('<b>Премьера</b>')
    # pos2 = wa_page.find('</table>', pos1)
    res = ''
    for i in range(3):
        pos = wa_page.find("class='review'>", pos) + 15
        res = wa_page[pos:pos + (2 if i < 2 else 4)] + ('-' + res if i > 0 else '')
    return res


def wa_notes(wa_page: str) -> str:
    """
    Функция извлечения примечаний из WA.
    :param wa_page: World Art страница (HTML-код).
    :return: Примечания.
    """
    pos1 = wa_page.find('<b>Тип</b>')
    pos2 = wa_page.find('</table>', pos1)
    pos1 = wa_page.find(' (', pos1, pos2) + 2
    if pos1 == 1:
        return ''
    pos1 = wa_page.find(' + ', pos1, pos2) + 1
    if pos1 == 0:
        return ''
    pos2 = wa_page.find('), ', pos1, pos2)
    return wa_page[pos1:pos2]


def extraction_anime_from_wa(page: str, mid: int = 0) -> dict:
    """
    Функция извлечения данных из страницы (HTML-кода) anime на World Art.
    :param page: Страница (HTML-код), возвращённый функцией search_anime_in_wa.
    :param mid: ID манги в БД. 0 — нет манги в БД.
    :return: Словарь данных.
    """
    oam = requests.get(f'{OAM}frmAddAnime.php', cookies=COOKIES_O).text
    res = {
        'anfor': wa_format_id(page, oam),
        'anstu[]': wa_studios_id(page, oam),
        'andir[]': wa_directors_id(page, oam),
        'genre[]': wa_genres_id(page, oam),
        'amnor': wa_name_orig(page),
        'amnro': wa_name_rom(page),
        'amnen': wa_name_eng(page),
        'amnru': wa_name_rus(page),
        'annep': wa_number_of_episodes(page),
        'andur': wa_duration(page),
        'amdpr': wa_date_of_premiere_anime(page),
        'notes': wa_notes(page)
    }
    if res['amnru'] == res['amnro']:
        res['amnru'] = ''
    dk = []
    for k, v in res.items():
        if not isinstance(v, int) and len(v) == 0:
            dk.append(k)
    for k in dk:
        del res[k]
    if mid:
        res['anman[]'] = mid
    res['ok'] = 'OK'
    return res


def wa_ann_poster(wa_page: str, mid: int, name: str, am: int = 0) -> None:
    """
    Функция поиска, загрузки и сохранения постера anime с сервера World Art или ANN
    в виде миниатюрной картинки для своей БД.
    :param wa_page: World Art страница (HTML-код).
    :param mid: ID в БД (возвращённое put_in_db).
    :param name: Наименование.
    :param am: Переключатель: 0 — anime, 1 — manga.
    """
    if am:
        pos = wa_page.find("<a href='img/")
    else:
        pos = wa_page.find(f"<a href='{WAA}{A}_poster.php?id=")
    if pos != -1:
        if am:
            url = f'{WAA}img/' + wa_page[pos + 13:wa_page.find("' ", pos)]
        else:
            pos = wa_page.find(f"<img src='{WAA}img/", pos)
            url = wa_page[pos + 10:wa_page.find("' ", pos)]
    else:
        if am:
            pos = wa_page.find("<tr><td align=left width=145 class='review' Valign=top><b>Сайты</b></td>")
        else:
            pos = wa_page.find('<tr><td class=bg2>&nbsp;<b>Сайты</b></td></tr>')
        pos = wa_page.find(ANN, pos) + (62 if am else 59)
        if pos == 61 if am else 58:
            with open(f'{PATH}{'m' if am else 'a'}/report.log', 'a', encoding='utf8') as file:
                file.write(f'{mid},"{name}","Нет постера."')
            return
        aid = int(wa_page[pos:wa_page.find("' ", pos)])
        ann = requests.get(f'{CANNE}api.xml',
                           {M if am else 'anime': aid}).text
        root = et.fromstring(ann)
        url = root[0].find('info').attrib['src']
    img = Image.open(urlopen(url))
    img.thumbnail((100, 100))
    img.save(f'{PATH}{'m' if am else 'a'}/{mid}.jpg')


# wa_page = search_in_wa(name, form, year)
# with open('page.html', 'w', encoding='utf8') as file:
#     file.write(wa_page)
# with open('page.html', 'w', encoding='utf8') as file:
#     file.write(requests.get(f'{OAM}frmAddManga.php', cookies=COOKIES_O).text)
if wa_anime_page := search_anime_in_wa(name, form, year):
    mid = 0
    if wa_manga_page := search_manga_in_wa_anime_page(wa_anime_page):
        pages = wa_manga_pages(wa_manga_page)
        for page in pages:
            # if page == pages[0]:
            #     continue
            data = extraction_manga_from_wa(page)
            mid = put_in_db(f'{OAM}frmAddManga.php', data)
            wa_ann_poster(page, mid, data['amnro'], 1)
    pages = wa_anime_pages(wa_anime_page)
    for page in pages:
        # if page == pages[0]:
        #     continue
        data = extraction_anime_from_wa(page, mid)
        aid = put_in_db(f'{OAM}frmAddAnime.php', data)
        wa_ann_poster(page, aid, data['amnro'])
