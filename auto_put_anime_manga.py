"""
Главный модуль.

Сокращения:
ANN — AnimeNewsNetwork,
MU — MangaUpdates,
WA — World Art,
WP — Wikipedia (en).
"""
from input import *
import world_art as wa
import animenewsnetwork as ann
import wikipedia_ as wp
import mangaupdates as mu
from decode_name import normal_name
from constants import *
import db
from Table import Table


def ann_pages_in_wa(_ann_anime_pages: dict[int, str], _ann_manga_pages: dict[int, str],
                    _wa_anime_pages: dict[int, str] | None, _wa_manga_pages: dict[int, str] | None
                    ) -> tuple[dict[int, str], dict[int, str], dict[int, int]]:
    """
    Получение XML-страниц из ANN по ссылкам в страницах WA.
    :param _ann_anime_pages: Словарь {ANN_ID: XML} XML-страниц anime из ANN.
    :param _ann_manga_pages: Словарь {ANN_ID: XML} XML-страниц манги из ANN.
    :param _wa_anime_pages: Словарь {WA_ID: HTML} HTML-страниц anime из WA либо None.
    :param _wa_manga_pages: Словарь {WA_ID: HTML} HTML-страниц манги из WA либо None.
    :return: Кортеж: словарь {ANN_ID: XML} XML-страниц anime из ANN, словарь {ANN_ID: XML} манги,
        словарь {ANN_ID anime: ANN_ID манги} адаптационных связей.
    """
    if _wa_anime_pages:
        for page in _wa_anime_pages.values():
            id_ = wa.ann_anime_id(page)
            if id_ and id_ not in _ann_anime_pages:
                _ann_anime_pages[id_] = ann.xml(id_)
    if _wa_manga_pages:
        for page in _wa_manga_pages.values():
            id_ = wa.ann_manga_id(page)
            if id_ and id_ not in _ann_manga_pages:
                _ann_manga_pages[id_] = ann.xml(id_)
    return ann.pages(_ann_anime_pages, _ann_manga_pages)


def wp_pages_in_wa(search: str) -> dict[str, str]:
    """
    Получение HTML-страниц из WP по ссылкам в страницах WA.
    :param search: Искомое наименование.
    :return: Словарь {WP_title_date: HTML} HTML-страниц из WP.
    """
    def proc():
        nonlocal _wp_pages
        wp_title = wa.wp_title(page)
        if wp_title:
            wp_title = normal_name(wp_title)
            if wp_title not in _wp_pages:
                _wp_pages.update(wp.search_pages(wp_title))

    _wp_pages = wp.search_pages(search)
    if wa_anime_pages:
        for page in wa_anime_pages.values():
            proc()
    if wa_manga_pages:
        for page in wa_manga_pages.values():
            proc()
    return _wp_pages


def mu_pages_in_wa(_mu_pages: dict[int, dict] | None, _wa_manga_pages: dict[int, str] | None) -> dict[int, dict] | None:
    """
    Получение JSON-ответов (основы или «выжимок» из страниц) от MU по ссылкам в страницах WA.
    :param _mu_pages: Словарь {MU_ID: JSON} данных по манге из MU либо None.
    :param _wa_manga_pages: Словарь {WA_ID: HTML} HTML-страниц манги из WA либо None.
    :return: Словарь {MU_ID: JSON} данных по манге из MU либо None.
    """
    if _wa_manga_pages:
        for page in _wa_manga_pages.values():
            mu_id = wa.mu_manga_id(page)
            if mu_id and (not _mu_pages or mu_id not in _mu_pages):
                _mu_pages = mu.search_pages_id(_mu_pages, mu_id)
    return _mu_pages


def notes(mdata: dict) -> str:
    """
    Формирование строки примечаний на основе значений следующих полей в словаре данных по манге:
        - количество томов,
        - количество глав,
        - дата премьеры.
    :param mdata: Словарь данных по манге.
    :return: Строка примечаний. Пустая строка, если примечаний нет.
    """
    v = True if not mdata['number_of_volumes'] else False
    c = True if not mdata['number_of_chapters'] or (
            mdata['number_of_volumes'] and mdata['number_of_volumes'] == mdata['number_of_chapters']) else False
    d = True if not mdata['date_of_premiere'] or (
            mdata['date_of_premiere'] and int(mdata['date_of_premiere'][8:]) > 27) else False
    return (f'{'Нет инф-и о' if v or c or d else ''}{' кол-ве' if v or c else ''}{' томов' if v else ''}'
            f'{',' if v and c else ''}{' глав' if c else ''}{' и' if (v or c) and d else ''}'
            f'{' точной дате премьеры' if d else ''}{'.' if v or c or d else ''}')


def data_join() -> dict[str, list[dict[str, str | list[dict[str, str]] | int | list[str] | None]]]:
    """
    Формирование единого словаря данных из словарей данных, извлечённых из страниц.
    :return: Единый словарь данных следующего формата:
        {'manga': Список_словарей_данных_по_манге, 'anime': Список_словарей_данных_по_anime}
    """
    def maut(_aut: dict[str, str]) -> bool:
        """
        Сверка имён (ромадзи и оригинальных) авторов манги.
        :param _aut: Словарь имён автора сравниваемой манги.
        :return: True — имена авторов совпадают. False — не совпадают.
        """
        for a in mdata['author_of_manga']:
            if (_aut['name_rom'] == a['name_rom'] or
                    ('name_orig' in _aut and 'name_orig' in a and
                     _aut['name_orig'] == a['name_orig'].replace(' ', ''))):
                return True
        return False

    def mwp(_i: int = 0) -> None:
        """
        Поиск соответствующей манги в словаре WP и дополнение недостающими данными единого словаря данных по манге.
        :param _i: Величина погрешности в указании года премьеры манги в WP относительно WA или ANN.
        """
        if wp_data and M in wp_data:
            nonlocal ids, mdata
            md = int(mdata['date_of_premiere'][:4])
            for wpt, wpdata in wp_data[M].items():
                q = False
                wpd = int(wpdata['date_of_premiere'][:4])
                if wpd == md or (_i and wpd == md + _i):
                    for aut in wpdata['author_of_manga']:
                        q = maut(aut)
                if q:
                    for tit in ('number_of_volumes', 'number_of_chapters'):
                        if (tit not in mdata or not mdata[tit]) and wpdata[tit]:
                            mdata[tit] = wpdata[tit]
                    for mp in wpdata['publication']:
                        if not len(mdata['publication']):
                            mdata['publication'] = wpdata['publication']
                            break
                        for ap in mdata['publication']:
                            if ap['publication'].replace(' ', '') == mp['publication'].replace(' ', ''):
                                break
                        else:
                            mdata['publication'].append(mp)
                    ids[M]['WP'].append(wpt)

    def mmu(_i: int = 0) -> None:
        """
        Поиск соответствующей манги в словаре MU и дополнение недостающими данными единого словаря данных по манге.
        :param _i: Величина погрешности в указании года премьеры манги в MU относительно WA, ANN или WP.
        """
        if mu_data:
            nonlocal mdata, ids
            md = int(mdata['date_of_premiere'][:4])
            for muid, mudata in mu_data.items():
                q = False
                mud = int(mudata['date_of_premiere'][:4])
                if mud == md or (_i and mud == md + _i):
                    for aut in mudata['author_of_manga'].values():
                        q = maut(aut)
                if q:
                    for tit in ('name_orig', 'name_rom', 'name_eng', 'name_rus',
                                'number_of_volumes', 'number_of_chapters', 'poster'):
                        if (tit not in mdata or not mdata[tit]) and mudata[tit]:
                            mdata[tit] = mudata[tit]
                        if tit in ('number_of_volumes', 'number_of_chapters') and not mdata[tit]:
                            mdata[tit] = 1
                    for aut in mudata['author_of_manga'].values():
                        for ma in mdata['author_of_manga']:
                            if (('name_orig' not in ma or not ma['name_orig']) and 'name_orig' in aut and
                                    aut['name_orig'] and aut['name_rom'] == ma['name_rom']):
                                ma['name_orig'] = aut['name_orig']
                                break
                    for mp in mudata['publication']:
                        if not len(mdata['publication']):
                            mdata['publication'] = mudata['publication']
                            break
                        for ap in mdata['publication']:
                            if ap['publication'].replace(' ', '') == mp['publication'].replace(' ', ''):
                                break
                        else:
                            mdata['publication'].append(mp)
                    if ('genre' not in mdata or not mdata['genre']) and len(mudata['genre']):
                        mdata['genre'].extend(mudata['genre'])
                    ids[M]['MU'].append(muid)

    def awp() -> None:
        """
        Поиск соответствующего anime в словаре WP и дополнение недостающими данными единого словаря данных по anime.
        """
        if wp_data and A in wp_data:
            nonlocal adata, ids
            ane = adata['number_of_episodes'] if adata['number_of_episodes'] else 1
            am = (int(adata['duration'][:2]) * 60 + int(adata['duration'][3:])) * ane
            c = False
            m = 0
            for wpt, wpdata in wp_data[A].items():
                q, qd = False, False
                if c or wpdata['date_of_premiere'] in adata['date_of_premiere']:
                    c, qd = False, True
                    for d in wpdata['director']:
                        for ad in adata['director']:
                            qd = False
                            if (d['name_rom'] in ad['name_rom'] or
                                    ('name_orig' in d and
                                     d['name_orig'].replace(' ', '') in ad['name_orig'])):
                                q = True
                                break
                            q = False
                    if wpdata['duration']:
                        ne = wpdata['number_of_episodes'] if wpdata['number_of_episodes'] else 1
                        m += (int(wpdata['duration'][:2]) * 60 + int(wpdata['duration'][3:])) * ne
                        if 0.85 * am > m:
                            c = True
                if q or qd:
                    for tit in ('name_eng', 'number_of_episodes', 'date_of_premiere'):
                        if not adata[tit] and wpdata[tit]:
                            adata[tit] = wpdata[tit]
                    if not len(adata['studio']) and len(wpdata['studio']):
                        adata['studio'] = wpdata['studio']
                    dd = []
                    for d in wpdata['director']:
                        qd = True
                        for ad in adata['director']:
                            if (d['name_rom'] in ad['name_rom'] or
                                    ('name_orig' in d and d['name_orig'].replace(' ', '') in ad['name_orig'])):
                                qd = False
                                break
                        if qd:
                            dd.append(d)
                    adata['director'].extend(dd)

    def not_none(_am: bool = True) -> dict:
        """
        Замена None в обязательных полях на значения по умолчанию (или заглушки).
        :param _am: Переключатель anime/манга (False/True).
        :return: Изменённый соответствующий словарь данных.
        """
        tit_v = {'date_of_premiere': '1900-12-31', 'genre': [22]}  # Индекс значения «—<Не определён>—».
        if _am:
            _res = mdata
            tit_v.update({'number_of_volumes': 1, 'number_of_chapters': 1})
        else:
            _res = adata
        for tit, v in tit_v.items():
            if not _res[tit]:
                _res[tit] = v
        return _res

    res = {M: [], A: []}
    ids = {M: {'WA': [], 'ANN': [], 'WP': [], 'MU': []}, A: {'WA': [], 'ANN': []}}

    # manga
    if M in wa_data:
        for waid, wadata in wa_data[M].items():
            mdata = {'author_of_manga': [], 'number_of_volumes': None, 'number_of_chapters': None,
                     'publication': [], 'poster': wadata['poster']}
            for tit in ('name_orig', 'name_rom', 'name_eng', 'name_rus', 'date_of_premiere'):
                mdata[tit] = wadata[tit] if wadata[tit] else None
            for tit in ('author_of_manga', 'publication'):
                if len(wadata[tit]):
                    for ap in wadata[tit].values():
                        mdata[tit].append(ap)
            if len(wadata['genre']):
                mdata['genre'] = wadata['genre']
            ids[M]['WA'].append(waid)
            if M in ann_data:
                md = int(mdata['date_of_premiere'][:4])
                for annid, anndata in ann_data[M].items():
                    q = False
                    annd = int(anndata['date_of_premiere'][:4])
                    if annd == md or annd == md + 1:
                        for aut in anndata['author_of_manga']:
                            q = maut(aut)
                    if not q and annid == wadata['ann']:
                        q = True
                    if q:
                        for tit in ('name_orig', 'name_rom', 'name_eng', 'name_rus', 'number_of_volumes', 'poster'):
                            if not mdata[tit] and anndata[tit]:
                                mdata[tit] = anndata[tit]
                        ids[M]['ANN'].append(annid)
            mwp(1)
            mmu(1)
            mdata['notes'] = notes(mdata)
            mdata = not_none()
            res[M].append(mdata)
    if M in ann_data:
        for annid, anndata in ann_data[M].items():
            if annid in ids[M]['ANN']:
                continue
            mdata = {}
            for tit in ('name_orig', 'name_rom', 'name_eng', 'name_rus',
                        'number_of_volumes', 'number_of_chapters', 'date_of_premiere', 'poster'):
                mdata[tit] = anndata[tit] if tit in anndata and anndata[tit] else None
            for tit in ('author_of_manga', 'genre'):
                mdata[tit] = anndata[tit] if tit in anndata and len(anndata[tit]) else []
            if len(anndata['publication']):
                mdata['publication'] = []
                for ap in anndata['publication'].values():
                    mdata['publication'].append(ap)
            ids[M]['ANN'].append(annid)
            mwp()
            mmu()
            mdata['notes'] = notes(mdata)
            mdata = not_none()
            res[M].append(mdata)
    if wp_data and M in wp_data:
        for wpt, wpdata in wp_data[M].items():
            if wpt in ids[M]['WP']:
                continue
            mdata = {
                'name_orig': None,
                'name_rom': None,
                'name_eng': wpdata['name_eng'] if wpdata['name_eng'] else wpt[:-13].title(),
                'name_rus': None,
                'author_of_manga': wpdata['author_of_manga'] if len(wpdata['author_of_manga']) else [],
                'number_of_volumes': wpdata['number_of_volumes'] if wpdata['number_of_volumes'] else None,
                'number_of_chapters': wpdata['number_of_chapters'] if wpdata['number_of_chapters'] else None,
                'date_of_premiere': wpdata['date_of_premiere'] if wpdata['date_of_premiere'] else None,
                'publication': wpdata['publication'],
                'genre': []
            }
            ids[M]['WP'].append(wpt)
            ip = len(mdata['publication'])
            for i in range(ip):
                if not mdata['publication'][ip - i - 1]['publication']:
                    mdata['publication'].pop(ip - i - 1)
            mmu()
            for tit in ('name_orig', 'name_rom'):
                if not mdata[tit] and mdata['name_eng']:
                    mdata[tit] = mdata['name_eng']
            for author in mdata['author_of_manga']:
                if 'name_rus' not in author:
                    people = wa.search_people(author['name_rom'])
                    if people:
                        author['name_rus'] = people['name_rus']
            mdata['notes'] = notes(mdata)
            mdata = not_none()
            res[M].append(mdata)
    if mu_data:
        for muid, mudata in mu_data.items():
            if muid in ids[M]['MU']:
                continue
            mdata = {'author_of_manga': [], 'publication': [], 'genre': []}
            for tit in ('name_orig', 'name_rom', 'name_eng', 'name_rus',
                        'number_of_volumes', 'number_of_chapters', 'date_of_premiere', 'poster'):
                mdata[tit] = mudata[tit] if mudata[tit] else None
            if len(mudata['author_of_manga']):
                for ap in mudata['author_of_manga'].values():
                    mdata['author_of_manga'].append(ap)
            if len(mudata['publication']):
                for ap in mudata['publication']:
                    mdata['publication'].append(ap)
            if len(mudata['genre']):
                mdata['genre'] = mudata['genre']
            ids[M]['MU'].append(muid)
            for author in mdata['author_of_manga']:
                if 'name_rus' not in author:
                    people = wa.search_people(author['name_rom'])
                    if people:
                        author['name_rus'] = people['name_rus']
            mdata['notes'] = notes(mdata)
            mdata = not_none()
            res[M].append(mdata)

    # anime
    if A in wa_data:
        for waid, wadata in wa_data[A].items():
            adata = {}
            for tit in ('name_orig', 'name_rom', 'name_eng', 'name_rus', 'format', 'number_of_episodes', 'duration',
                        'date_of_premiere'):
                adata[tit] = wadata[tit] if wadata[tit] else None
            for tit in ('studio', 'director', 'genre'):
                adata[tit] = wadata[tit] if wadata[tit] is not None and len(wadata[tit]) else []
            adata['notes'] = wadata['notes'] if wadata['notes'] else None
            adata.update({'poster': wadata['poster'], M: None})
            if M + '_id' in wadata:
                adata[M] = []
                i = 0
                for mid in wa_data[M].keys():
                    if mid == wadata[M + '_id']:
                        adata[M].append(i)
                        break
                    i += 1
            ids[A]['WA'].append(waid)
            for annid, anndata in ann_data[A].items():
                q, qd = False, False
                if (anndata['date_of_premiere'] in adata['date_of_premiere'] or
                        int(anndata['date_of_premiere'][:4]) == int(adata['date_of_premiere'][:4])):
                    qd = True
                    for d in anndata['director']:
                        for ad in adata['director']:
                            qd = False
                            if (d['name_rom'] in ad['name_rom'] or
                                    ('name_orig' in d and d['name_orig'].replace(' ', '') in ad['name_orig'])):
                                q = True
                                break
                            q = False
                if not q and annid == wadata['ann']:
                    q = True
                if q or qd:
                    for tit in ('name_orig', 'name_rom', 'name_eng', 'name_rus',
                                'number_of_episodes', 'date_of_premiere'):
                        if not adata[tit] and anndata[tit]:
                            adata[tit] = anndata[tit]
                    if not len(adata['studio']) and len(anndata['studio']):
                        adata['studio'] = anndata['studio']
                    dd = []
                    for d in anndata['director']:
                        qd = True
                        for ad in adata['director']:
                            if (d['name_rom'] in ad['name_rom'] or
                                    ('name_orig' in d and d['name_orig'].replace(' ', '') in ad['name_orig'])):
                                qd = False
                                break
                        if qd:
                            dd.append(d)
                    if ('director' not in adata or len(adata['director']) == 0) and len(dd) > 0:
                        adata['director'] = dd
                    if not adata[M] and M + '_id' in anndata:
                        adata[M] = []
                        i = 0
                        for mid in ann_data[M].keys():
                            if mid == anndata[M + '_id']:
                                adata[M].append(i)
                                break
                            i += 1
                    ids[A]['ANN'].append(annid)
            awp()
            adata = not_none(False)
            res[A].append(adata)
    if A in ann_data:
        for annid, anndata in ann_data[A].items():
            if annid in ids[A]['ANN']:
                continue
            adata = {}
            for tit in ('name_orig', 'name_rom', 'name_eng', 'name_rus', 'format', 'number_of_episodes', 'duration',
                        'date_of_premiere'):
                adata[tit] = anndata[tit] if tit in anndata and anndata[tit] else None
            for tit in ('studio', 'director', 'genre'):
                adata[tit] = anndata[tit] if tit in anndata and anndata[tit] is not None and len(anndata[tit]) else []
            adata['notes'] = anndata['notes'] if 'notes' in anndata and anndata['notes'] else None
            adata.update({'poster': anndata['poster'], M: None})
            if M + '_id' in anndata:
                adata[M] = []
                i = 0
                for mid in ann_data[M].keys():
                    if mid == anndata[M + '_id']:
                        adata[M].append(i)
                        break
                    i += 1
            ids[A]['ANN'].append(annid)
            awp()
            for author in adata['director']:
                if 'name_rus' not in author:
                    people = wa.search_people(author['name_rom'])
                    if people:
                        author['name_rus'] = people['name_rus']
            adata = not_none(False)
            res[A].append(adata)
    return res


def title_unique(_data: dict[str, list[dict[str, str | list[dict[str, str]] | int | list[str] | None]]]
                 ) -> dict[str, list[dict[str, str | list[dict[str, str]] | int | list[str] | None]]]:
    """
    Устранение одноимённости разных anime и манги.
    Если попадаются, например, две одноимённые экранизации (anime), то более поздней в наименовании добавляется год.
    :param _data: Единый словарь данных.
    :return: Единый словарь данных.
    """
    for m in (M, A):
        titles = [(a['name_orig'], a['name_rom'], a['date_of_premiere']) for a in _data[m]]
        lt = len(titles)
        for a in range(lt - 1):
            for b in range(a + 1, lt):
                if titles[a][0] == titles[b][0]:
                    if int(titles[a][2][:4]) < int(titles[b][2][:4]):
                        _data[m][b]['name_orig'] += f" ({titles[b][2][:4]})"
                    elif int(titles[a][2][:4]) > int(titles[b][2][:4]):
                        _data[m][a]['name_orig'] += f" ({titles[a][2][:4]})"
                if normal_name(titles[a][1]) == normal_name(titles[b][1]):
                    if int(titles[a][2][:4]) < int(titles[b][2][:4]):
                        _data[m][b]['name_rom'] += f" ({titles[b][2][:4]})"
                    elif int(titles[a][2][:4]) > int(titles[b][2][:4]):
                        _data[m][a]['name_rom'] += f" ({titles[a][2][:4]})"
    return _data


def control(_data: dict[str, list[dict[str, str | list[dict[str, str]] | int | list[str] | None]]]
            ) -> dict[str, list[dict[str, str | list[dict[str, str]] | int | list[str] | bool | None]]]:
    """
    Вывод единого словаря данных пользователю и запрос указания добавляемых в БД данных.
    :param _data: Единый словарь данных.
    :return: Единый словарь данных для сохранения.
    """
    for _am, els in _data.items():
        print(Table(els, _am.title()))
    lm = len(_data[M])
    sav = input("Номера добавляемых в БД кортежей (через пробел), либо «*» для всех: ").split()
    if sav[0] == "*":
        sav = list(range(1, lm + len(_data[A]) + 1))
    i = 0
    sav_data = {}
    for _am, els in _data.items():
        sav_data[_am] = []
        for el in els:
            sav_data[_am].append(el)
            i += 1
            sav_data[_am][i - 1 - (lm if _am == A else 0)]['save'] = True if str(i) in sav or i in sav else False
    return sav_data


if __name__ == '__main__':
    # Поиск и сбор страниц
    wa_anime_pages = wa.search_anime(title, year, form) if A_M == A else None
    wa_manga_pages = wa.search_manga(title, year) if A_M == M else None
    ann_anime_pages, ann_manga_pages, ann_rm = ann.search_pages(title, year, form)
    mu_pages = mu.search_pages(title, year) if A_M == M else None
    if not mu_pages:
        mu_pages = mu.search_pages(title)
    if wa_anime_pages and len(wa_anime_pages):
        wa_manga_pages, wa_rm = wa.manga_pages_from_anime(wa_manga_pages, wa_anime_pages)
    if wa_manga_pages and len(wa_manga_pages):
        wa_anime_pages = wa.anime_pages_from_manga(wa_anime_pages, wa_manga_pages)
    ann_anime_pages, ann_manga_pages, ann_rm = ann_pages_in_wa(ann_anime_pages, ann_manga_pages, wa_anime_pages,
                                                               wa_manga_pages)
    wp_pages = wp_pages_in_wa(title)
    wp_page_parts = wp.filter_page_parts(wp.manga_anime_in_page(wp_pages))
    if not len(wp_page_parts):
        wp_pages = wp_pages_in_wa(f'{title} {M}')
        wp_page_parts = wp.filter_page_parts(wp.manga_anime_in_page(wp_pages))
    if not len(wp_page_parts):
        wp_pages = wp_pages_in_wa(f'{title.replace("ou", "o")} {M}')
        wp_page_parts = wp.filter_page_parts(wp.manga_anime_in_page(wp_pages))
    mu_pages = mu_pages_in_wa(mu_pages, wa_manga_pages)

    # Извлечение данных из страниц
    wa_data = {}
    if wa_manga_pages and len(wa_manga_pages):
        wa_data[M] = {id_: wa.extraction_manga(page) for id_, page in wa_manga_pages.items()}
    if wa_anime_pages and len(wa_anime_pages):
        wa_data[A] = {id_: wa.extraction_anime(page, wa_rm[id_] if id_ in wa_rm else None)
                      for id_, page in wa_anime_pages.items()}
    ann_data = {}
    if ann_manga_pages and len(ann_manga_pages):
        ann_data[M] = {id_: ann.extraction_manga(id_, ann_xml) for id_, ann_xml in ann_manga_pages.items()}
    if ann_anime_pages and len(ann_anime_pages):
        ann_data[A] = {id_: ann.extraction_anime(ann_xml, ann_rm[id_] if id_ in ann_rm else None)
                       for id_, ann_xml in ann_anime_pages.items()}
    wp_data = wp.extraction_data(wp_page_parts, wp_pages) if len(wp_page_parts) else None
    mu_data = {id_: mu.extraction_manga(page) for id_, page in mu_pages.items()} if mu_pages and len(mu_pages) else None

    # Формирование единого словаря данных
    data = title_unique(data_join())

    # Контроль и выбор
    data = control(data)

    # Добавление данных в БД
    am = db.DB()
    if len(data[M]):
        for i, md in enumerate(data[M]):
            mid = am.get_manga_id(md)
            if md['save'] and not mid:
                mid = am.add_manga(md)
                if 'poster' in md and md['poster']:
                    db.save_poster(md['poster'], mid, True)
            # Прописывание нового ID манги в связи anime
            for a in range(len(data[A])):
                if data[A][a][M]:
                    for m in range(len(data[A][a][M])):
                        if data[A][a][M][m] == i:
                            data[A][a][M][m] = mid
    if len(data[A]):
        for ad in data[A]:
            aid = am.get_anime_id(ad)
            if ad['save'] and not aid:
                aid = am.add_anime(ad)
                if 'poster' in ad and ad['poster']:
                    db.save_poster(ad['poster'], aid)
