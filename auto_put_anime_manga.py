import requests
from time import sleep
import xml.etree.ElementTree as et
import json
import wikipedia
from wikipedia.exceptions import PageError as WPPageError

from input import *
from config import *
from constants import *
import world_art as wa
import animenewsnetwork as ann
import wikipedia_ as wp
import decode_name as dn
import db
import mangaupdates as mu


def del_empty(data: dict) -> dict:
    """
    Удаление пустых полей.
    :param data: Словарь данных.
    :return: Словарь данных, очищенный от пустых полей.
    """
    dk = []
    for k, v in data.items():
        if not isinstance(v, int) and len(v) == 0:
            dk.append(k)
    for k in dk:
        del data[k]
    return data


def extraction_manga_from_wa(wa_page: str) -> dict:
    """
    Извлечение данных из страницы (HTML-кода) манги на World Art. Недостающие данные ищутся на ANN.
    :param wa_page: Страница (HTML-код), возвращённый функцией wa.search_manga_in_anime_page.
    :return: Словарь данных.
    """
    global ann_pages, mu_pages
    nnv = False  # Флаг добавления в примечания томов.
    wp_page = None
    ann_page, ann_pages = wa.manga_in_ann(wa_page, ann_pages)
    amnro = wa.manga_name_r(wa.name_rom, wa_page, 1)
    amnro_ = dn.normal_name(amnro)
    if ann_page:
        nv = ann.number_of_volumes(ann_page)
        ann_pages = ann.manga_pages(ann_page, ann_pages)
    elif wp_page := wikipedia.page(amnro_).html():  # wa.manga_in_wp(wa_page)
        nv = wp.number_of_volumes(wp_page)
    else:
        nv = 1
        nnv = True
    if not nv:
        ann_page = ann.manga_from_anime(wa.anime_in_ann(wa_anime_page))
        nv = ann.number_of_volumes(ann_page)
    if not len(mu_pages):
        mu_id = wa.id_manga_in_mu(wa_page)
        if mu_id:
            mu_json = mu.manga_json(mu_id)
            mu_pages = mu.related_manga(mu_json)
    if len(mu_pages):
        for mup in mu_pages:
            if dn.normal_name(mup['name']) == amnro_:
                mup['add'] = False  # Манга обработана и из MangaUpdates отдельно извлекать не нужно.
                break
    if not wp_page:
        wp_page = wikipedia.page(amnro_).html()  # wa.manga_in_wp(wa_page)
    amnen = wa.name_eng(wa_page, 1) or ann.title(ann_page, 'eng')
    if not (date_of_premiere := wp.date_of_premiere_manga(wp_page, amnro, amnen)):
        if not (date_of_premiere := ann.date_of_premiere_manga(ann_page)):
            date_of_premiere = wa.date_of_premiere_manga(wa_page)
    if date_of_premiere[5:] == '12-31':
        date_of_premiere = ann.date_of_premiere_manga(ann_page)
    nd = True if date_of_premiere and (date_of_premiere[8:9] == '3' or date_of_premiere[5:] == '02-28' or
                                       date_of_premiere[5:] == '02-29') else False
    if not date_of_premiere:
        date_of_premiere = '1900-01-01'
    amnru = wa.manga_name_r(wa.name_rus, wa_page)
    if amnru == amnro and mu_json:
        amnru = mu.select_title(mu_json, 'rus')
    oam = db.page('Manga')
    res = {
        'maaum[]': wa.authors_of_manga_id(wa_page, oam),
        'mapbc[]': wa.publications_id(wa_page, oam),
        'genre[]': wa.genres_id(wa_page, oam),
        'amnor': wa.name_orig(wa_page, 1),
        'amnro': amnro,
        'amnen': amnen,
        'amnru': amnru,
        'manvo': nv,
        'manch': nv,  # number_of_chapters(ann_page),
        'amdpr': date_of_premiere,
        'notes': f'Нет инф-и о кол-ве{' томов,' if nnv else ''} глав{' и точной дате премьеры' if nd else ''}.'
    }
    if res['amnru'] == res['amnro']:
        res['amnru'] = ''
    if res['amnen'] == '' and res['amnor'] == res['amnro']:
        res['amnen'] = res['amnro']
    return del_empty(res)


def extraction_anime_from_wa(page: str, mid: int = 0) -> dict:
    """
    Извлечение данных из страницы (HTML-кода) anime на World Art.
    :param page: Страница (HTML-код), возвращённый функцией wa.search_anime.
    :param mid: ID манги в БД. 0 — нет манги в БД.
    :return: Словарь данных.
    """
    oam = db.page('Anime')
    res = {
        'anfor': wa.format_id(page, oam),
        'anstu[]': wa.studios_id(page, oam),
        'andir[]': wa.directors_id(page, oam),
        'genre[]': wa.genres_id(page, oam),
        'amnor': wa.name_orig(page),
        'amnro': wa.name_rom(page),
        'amnen': wa.name_eng(page) or ann.title(wa.anime_in_ann(page), 'eng'),
        'amnru': wa.name_rus(page),
        'annep': wa.number_of_episodes(page),
        'andur': wa.duration(page),
        'amdpr': wa.date_of_premiere_anime(page),
        'notes': wa.notes(page)
    }
    if res['amnru'] == res['amnro']:
        res['amnru'] = ''
    if res['amnor'] == res['amnru'] and res['amnro'] != '':
        res['amnor'] = res['amnro']
    if res['amnen'] == '' and res['amnor'] == res['amnro']:
        res['amnen'] = res['amnro']
    res = del_empty(res)
    if mid:
        res['anman[]'] = mid
    return res


def wa_ann_poster(wa_page: str, mid: int, name: str, am: int | bool = 0) -> None:
    """
    Поиск, загрузка и сохранение постера с сервера World Art или ANN
    в виде миниатюрной картинки для своей БД.
    :param wa_page: World Art страница (HTML-код).
    :param mid: ID в БД (возвращённое db.put).
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
        pos = wa_page.find("<tr><td align=left width=145 class='review' Valign=top><b>Сайты</b></td>" if am else
                           '<tr><td class=bg2>&nbsp;<b>Сайты</b></td></tr>')
        pos = wa_page.find(ANN, pos) + (54 if am else 51)
        if pos == (53 if am else 50):
            with open(f'{PATH}{'m' if am else 'a'}/report.log', 'a', encoding='utf8') as file:
                file.write(f'{mid},"{name}","Нет постера."')
            return
        aid = int(wa_page[pos:wa_page.find("' ", pos)])
        ann = requests.get(f'{CANNE}api.xml', {M if am else 'anime': aid}).text
        root = et.fromstring(ann)
        url = root[0].find('info').attrib['src']
    db.save_poster(url, mid, am)


def search_manga_in_mu(ann_xml: str) -> json.JSONEncoder | None:
    """
    Поиск страницы манги на MangaUpdates.
    :param ann_xml: XML-страница ANN.
    :return: Данные по манге с MangaUpdates в JSON-формате. None, если манги нет.
    """
    global mu_pages
    pos1 = ann_xml.find('type="Main title" lang="') + 28
    pos2 = ann_xml.find('</info>', pos1)
    search = dn.normal_name(ann_xml[pos1:pos2])
    for mup in mu_pages:
        if dn.normal_name(mup['name']) == search:
            mup['add'] = False
            return mu.manga_json(mup['id'])
    data = requests.post(AMUS + 'search', {'search': search}).json()
    for res in data['results']:
        if dn.normal_name(res['hit_title']) == search:
            mu_pages.append({'id': res['record']['series_id'], 'name': res['hit_title'], 'add': False})
            return mu.manga_json(res['record']['series_id'])


def put_publication_ann(publication: dict) -> int:
    """
    Добавление издания в БД и возврата ID.
    :param publication: Издание.
    :return: ID издания в БД.
    """
    pp = wa.search_publication_or_publishing(publication['name'])
    publishing = ann.search_publishing(ann_id) if not pp else wa.extraction_publishing(pp)
    return db.put_publication({'name': publication['name'], 'type': publication['type'], 'publishing': publishing})


def extraction_manga_from_ann(ann_xml: str) -> dict:
    """
    Извлечение данных из страницы (XML) манги на ANN.
    :param ann_xml: XML-страница.
    :return: Словарь данных.
    """
    if not (mu_json := search_manga_in_mu(ann_xml)):
        amnro = ann.title(ann_xml, 'rom')
    else:
        amnro = mu_json['title']
    oam = db.page('Manga')
    sleep(1)
    try:
        wp_page = wikipedia.page(amnro).html()
    except WPPageError:
        wp_page = wikipedia.page(title).html()
    date_of_premiere = None
    publications_id = None
    if mu_json:
        publications_id = mu.publications_id(mu_json, oam)
    amnen = ann.title(ann_xml, 'eng') or mu.select_title(mu_json, 'eng')
    if not publications_id:
        publications_id = wp.publications_id(amnro, amnen, wp_page, oam)
        if not publications_id:
            (publications_id, date_of_premiere), nd = ann.publications_id_and_date_of_premiere(
                ann_xml, oam, put_publication_ann
            ), False
    genres = ann.genres_id(ann_xml, oam) if not mu_json else mu.genres_id(mu_json, oam)
    if not len(genres):
        genres = db.select_genres(oam, amnro)
    if not date_of_premiere:
        date_of_premiere = wp.date_of_premiere_manga(wp_page, amnro, amnen)
    nd = True if date_of_premiere and date_of_premiere[5:] == '12-31' else False
    if not date_of_premiere:
        date_of_premiere = '1900-01-01'
    nnv = True
    nv = ann.number_of_volumes(ann_xml) or (0 if not mu_json else mu.volumes(mu_json))
    if nv:
        nnv = False
    else:
        nv = 1
    res = {
        'maaum[]': ann.authors_of_manga_id(ann_xml, oam),
        'mapbc[]': publications_id,
        'genre[]': genres,
        'amnor': ann.title(ann_xml, 'orig'),
        'amnro': amnro,
        'amnen': amnen,
        # 'amnru': ann.title(ann_xml, 'rus'),
        'manvo': nv,
        'manch': nv,  # ann.number_of_chapters(ann_xml),
        'amdpr': date_of_premiere,
        'notes': f'Нет инф-и о кол-ве{' томов,' if nnv else ''}{'' if nd else ' и' if nnv else ''} глав'
                 f'{' и точной дате премьеры' if nd else ''}.'
    }
    if not res['amnor']:
        res['amnor'] = res['amnro']
    # if res['amnru'] == res['amnro']:
    #     res['amnru'] = ''
    return del_empty(res)


def extraction_manga_from_mu(mu_json: json.JSONEncoder) -> dict:
    """
    Извлечение данных из страницы (JSON) манги на MangaUpdates.
    :param mu_json: Данные по манге с MangaUpdates в JSON-формате.
    :return: Словарь данных.
    """
    nnc = None
    nv = mu.volumes(mu_json)
    if nv < 0:
        nc = -nv
        nv = 1
    else:
        nc = nv
        nnc = True
    oam = db.page('Manga')
    genres = mu.genres_id(mu_json, oam)
    if not len(genres):
        genres = db.select_genres(oam, mu_json['title'])
    res = {
        'maaum[]': mu.authors_of_manga_id(mu_json, oam),
        'mapbc[]': mu.publications_id(mu_json, oam),
        'genre[]': genres,
        'amnor': mu.select_title(mu_json, 'orig'),
        'amnro': mu_json['title'],
        'amnen': mu.select_title(mu_json, 'eng'),
        'amnru': mu.select_title(mu_json, 'rus'),
        'manvo': nv,
        'manch': nc,
        'amdpr': mu_json['year'] + '-12-31',
        'notes': f'Нет инф-и о{' кол-ве глав и' if nnc else ''} точной дате премьеры.'
    }
    if not res['amnor']:
        res['amnor'] = res['amnro']
    return del_empty(res)


mu_pages = mu.related_manga_title(title)  # [dict(id=mu_id: int, name=name: str, add=добавлять?: bool)]
ann_pages = dict()  # {ann_id: обработана?}
if wa_anime_page := wa.search_anime(title, form, year):
    mid = 0
    if wa_manga_page := wa.search_manga_in_anime_page(wa_anime_page):
        pages = wa.manga_pages(wa_manga_page)
        for page in pages:
            # if page == pages[0]:
            #     continue
            data = extraction_manga_from_wa(page)
            mid = db.put('Manga', data)
            wa_ann_poster(page, mid, data['amnro'], 1)
    pages = wa.anime_pages(wa_anime_page)
    for page in pages:
        # if page == pages[0]:
        #     continue
        data = extraction_anime_from_wa(page, mid)
        aid = db.put('Anime', data)
        wa_ann_poster(page, aid, data['amnro'])
    for ann_id, done in ann_pages.items():
        if not done:
            sleep(1)
            page = requests.get(f'{CANNE}api.xml', {M: ann_id}).text
            data = extraction_manga_from_ann(page)
            # if ann_id in (,):
            #     continue
            mid = db.put('Manga', data)
            ann.poster(page, mid, data['amnro'])
    for mup in mu_pages:
        if mup['add']:
            mu_json = mu.manga_json(mup['id'])
            data = extraction_manga_from_mu(mu_json)
            mid = db.put('Manga', data)
            mu.poster(mu_json, mid, data['amnro'])
