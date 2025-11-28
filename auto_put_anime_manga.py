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
from decode_name import normal_name, o_ou, month
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
    :return: Словарь {WP_title: HTML} HTML-страниц из WP.
    """
    def proc():
        nonlocal _wp_pages
        wp_title = wa.wp_title(page)
        if wp_title:
            wp_title = wp_title.replace('_', ' ')
            if wp_title not in _wp_pages:
                _wp_pages = wp.search_pages(wp_title, _wp_pages)

    _wp_pages = wp.search_pages(normal_name(search))
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


def wa_pages_update(mode: str) -> None:
    """
    Обновление словарей HTML-страниц anime и манги из WA текущими данными.
    :param mode: Режим определения текущих данных: «ann», «wp».
    """
    global wa_anime_pages, wa_manga_pages
    if mode not in ("ann", "wp"):
        print(f"wa_pages_update: Некорректный аргумент mode='{mode}'")
        return
    tmp = None
    if am == A:
        if mode == "ann":
            tmp = wa.search_anime(o_ou(data['name_rom']), int(data['date_of_premiere'][:4]), data['format'],
                                  wa_anime_pages, wa_id['anime'])
        elif mode == "wp":
            tmp = wa.search_anime(wptit[:-13], int(wptit[-11:-7]), data['format'], wa_anime_pages, wa_id['anime'])
        if tmp:
            wa_anime_pages.update(tmp)
    else:
        if mode == "ann":
            tmp = wa.search_manga(o_ou(data['name_rom']), int(data['date_of_premiere'][:4]),
                                  wa_manga_pages, wa_id['manga'])
        elif mode == "wp":
            tmp = wa.search_manga(wptit[:-13], int(wptit[-11:-7]), wa_manga_pages, wa_id['manga'])
        if tmp:
            wa_manga_pages.update(tmp)


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
            mdata['date_of_premiere'] and mdata['date_of_premiere'] == month(mdata['date_of_premiere'])) else False
    return (f'{'Нет инф-и о' if v or c or d else ''}{' кол-ве' if v or c else ''}{' томов' if v else ''}'
            f'{',' if v and c else ''}{' глав' if c else ''}{' и' if (v or c) and d else ''}'
            f'{' точной дате премьеры' if d else ''}{'.' if v or c or d else ''}')


def data_join() -> dict[str, list[dict[str, str | list[dict[str, str]] | int | list[str] | None]]]:
    """
    Формирование единого словаря данных из словарей данных, извлечённых из страниц.
    :return: Единый словарь данных следующего формата:
        {'manga': Список_словарей_данных_по_манге, 'anime': Список_словарей_данных_по_anime}
    """
    def maut(_aut: list[dict[str, str]]) -> bool:
        """
        Сверка имён (ромадзи и оригинальных) авторов манги.
        :param _aut: Список словарей имён авторов сравниваемой манги.
        :return: True — имена авторов совпадают. False — не совпадают.
        """
        for aut in _aut:
            for a in mdata['author_of_manga']:
                if (aut['name_rom'] == a['name_rom'] or
                        ('name_orig' in aut and 'name_orig' in a and
                         aut['name_orig'] == a['name_orig'].replace(' ', ''))):
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
                wpd = int(wpdata['date_of_premiere'][:4])
                if (((mdata['date_of_premiere'] == wpdata['date_of_premiere'] and
                      wpdata['date_of_premiere'][5:] != "12-31") or
                     (wpdata['date_of_premiere'][5:] == "12-31" and (wpd == md or (_i and wpd == md + _i))) or
                     (normal_name(mdata['name_rom']) in (normal_name(wpdata['name_eng']), normal_name(wpt[:-13])) or
                      (mdata['name_eng'] and
                       normal_name(mdata['name_eng']) in (normal_name(wpdata['name_eng']), normal_name(wpt[:-13])))))
                        and maut(wpdata['author_of_manga'])):
                    for tit in ('number_of_volumes', 'number_of_chapters'):
                        if (tit not in mdata or not mdata[tit]) and wpdata[tit]:
                            mdata[tit] = wpdata[tit]
                    if not len(mdata['publication']):
                        mdata['publication'] = wpdata['publication']
                    ids[M]['WP'].append(wpt)
                    break

    def mmu(_i: int = 0) -> None:
        """
        Поиск соответствующей манги в словаре MU и дополнение недостающими данными единого словаря данных по манге.
        :param _i: Величина погрешности в указании года премьеры манги в MU относительно WA, ANN или WP.
        """
        if mu_data:
            nonlocal mdata, ids
            md = int(mdata['date_of_premiere'][:4])
            for muid, mudata in mu_data.items():
                mud = int(mudata['date_of_premiere'][:4])
                if (((mdata['date_of_premiere'] == mudata['date_of_premiere'] and
                      mudata['date_of_premiere'][5:] != "12-31") or
                     (mudata['date_of_premiere'][5:] == "12-31" and (mud == md or (_i and mud == md + _i))) or
                     (mdata['name_eng'] and normal_name(mdata['name_eng']) == normal_name(mudata['name_eng']))) and
                        maut(list(mudata['author_of_manga'].values()))):
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
                    if not len(mdata['publication']):
                        mdata['publication'] = mudata['publication']
                    if ('genre' not in mdata or not mdata['genre']) and len(mudata['genre']):
                        mdata['genre'].extend(mudata['genre'])
                    ids[M]['MU'].append(muid)
                    break

    def awp() -> None:
        """
        Поиск соответствующего anime в словаре WP и дополнение недостающими данными единого словаря данных по anime.
        """
        if wp_data and A in wp_data:
            nonlocal adata, ids
            c = False
            if adata['duration']:
                ane = adata['number_of_episodes'] if adata['number_of_episodes'] else 1
                am = (int(adata['duration'][:2]) * 60 + int(adata['duration'][3:])) * ane
                m = 0
            for wpt, wpdata in wp_data[A].items():
                q = qd = False
                if c or wpdata['date_of_premiere'] == adata['date_of_premiere']:
                    c, qd = False, True
                    for d in wpdata['director']:
                        for ad in adata['director']:
                            qd = False
                            if (d['name_rom'] == ad['name_rom'] or
                                    ('name_orig' in d and
                                     d['name_orig'].replace(' ', '') == ad['name_orig'])):
                                q = True
                                break
                            q = False
                    if wpdata['duration'] and adata['duration']:
                        ne = wpdata['number_of_episodes'] if wpdata['number_of_episodes'] else 1
                        m += (int(wpdata['duration'][:2]) * 60 + int(wpdata['duration'][3:])) * ne
                        if 0.85 * am > m:
                            c = True
                nwpt = normal_name(wpt[:-13])
                if q or qd or (((adata['name_eng'] and nwpt == normal_name(adata['name_eng'])) or
                                nwpt == normal_name(adata['name_rom'])) and
                               wpdata['date_of_premiere'][:4] == adata['date_of_premiere'][:4]):
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
                            if 'name_rus' not in d:
                                d = wa.search_people(d['name_rom'])
                            if d:
                                dd.append(d)
                    adata['director'].extend(dd)
                    if not c:
                        break

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
            tit_v.update({'studio': [1]})  # Индекс значения «—<Нет информации>—».
        for tit, v in tit_v.items():
            if not _res[tit]:
                _res[tit] = v
        return _res

    print("data_join()")
    res = {M: [], A: []}
    ids = {M: {'ANN': [], 'WP': [], 'MU': []}, A: {'ANN': []}}

    # manga
    if M in wa_data:
        for waid, wadata in wa_data[M].items():
            mdata = {'wa_id': waid, 'author_of_manga': [], 'number_of_volumes': None, 'number_of_chapters': None,
                     'publication': [], 'poster': wadata['poster']}
            for tit in ('name_orig', 'name_rom', 'name_eng', 'name_rus', 'date_of_premiere'):
                mdata[tit] = wadata[tit] if wadata[tit] else None
            for tit in ('author_of_manga', 'publication'):
                if len(wadata[tit]):
                    for ap in wadata[tit].values():
                        mdata[tit].append(ap)
            if len(wadata['genre']):
                mdata['genre'] = wadata['genre']
            if M in ann_data:
                md = int(mdata['date_of_premiere'][:4])
                for annid, anndata in ann_data[M].items():
                    annd = int(anndata['date_of_premiere'][:4])
                    if int(annid) == wadata['ann'] or (
                            (annd == md or annd == md + 1) and anndata['name_rom'] and
                            normal_name(anndata['name_rom']).
                                    replace("ou", "o") == normal_name(mdata['name_rom']).replace("ou", "o") and
                            maut(anndata['author_of_manga'])):
                        for tit in ('name_orig', 'name_rom', 'name_eng', 'name_rus', 'number_of_volumes', 'poster'):
                            if not mdata[tit] and anndata[tit]:
                                mdata[tit] = anndata[tit]
                        mdata['ann_id'] = annid
                        ids[M]['ANN'].append(annid)
                        break
            mwp(1)
            mmu(1)
            mdata['notes'] = notes(mdata)
            mdata = not_none()
            res[M].append(mdata)
    if M in ann_data:
        for annid, anndata in ann_data[M].items():
            if annid in ids[M]['ANN']:
                continue
            mdata = {'ann_id': annid}
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
            mwp(1)
            mmu(1)
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
                'name_eng': wpdata['name_eng'] if wpdata['name_eng'] else wpt[:-13],
                'name_rus': None,
                'author_of_manga': wpdata['author_of_manga'] if len(wpdata['author_of_manga']) else [],
                'number_of_volumes': wpdata['number_of_volumes'] if wpdata['number_of_volumes'] else None,
                'number_of_chapters': wpdata['number_of_chapters'] if wpdata['number_of_chapters'] else None,
                'date_of_premiere': wpdata['date_of_premiere'] if wpdata['date_of_premiere'] else None,
                'publication': wpdata['publication'],
                'genre': []
            }
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
                for i in range(len(res[M])):
                    if 'wa_id' in res[M][i] and int(res[M][i]['wa_id']) == wadata[M + '_id']:
                        adata[M].append(i)
                        break
            for annid, anndata in ann_data[A].items():
                q = qd = qid = False
                if int(annid) == wadata['ann']:
                    qid = True
                if not qid and (((anndata['date_of_premiere'][5:] != "12-31" and
                                  anndata['date_of_premiere'] == adata['date_of_premiere']) or
                                 (anndata['date_of_premiere'][5:] == "12-31" and
                                  anndata['date_of_premiere'][:4] == adata['date_of_premiere'][:4])) and
                                ((anndata['name_rom'] and normal_name(anndata['name_rom']).
                                        replace("ou", "o") == normal_name(adata['name_rom']).replace("ou", "o")) or
                                 (anndata['name_eng'] and adata['name_eng'] and normal_name(anndata['name_eng']).
                                         replace("ou", "o") == normal_name(adata['name_eng']).replace("ou", "o"))) and
                                maut(anndata['author_of_manga'])):
                    qd = True
                    for d in anndata['director']:
                        for ad in adata['director']:
                            qd = False
                            if (d['name_rom'] == ad['name_rom'] or
                                    ('name_orig' in d and d['name_orig'].replace(' ', '') == ad['name_orig'])):
                                q = True
                                break
                            q = False
                if qid or q or qd:
                    for tit in ('name_orig', 'name_rom', 'name_eng', 'name_rus',
                                'number_of_episodes', 'date_of_premiere'):
                        if not adata[tit] and anndata[tit]:
                            adata[tit] = anndata[tit]
                    if not len(adata['studio']) and 'studio' in anndata and len(anndata['studio']):
                        adata['studio'] = anndata['studio']
                    dd = []
                    for d in anndata['director']:
                        qd = True
                        for ad in adata['director']:
                            if (d['name_rom'] == ad['name_rom'] or
                                    ('name_orig' in d and d['name_orig'].replace(' ', '') == ad['name_orig'])):
                                qd = False
                                break
                        if qd:
                            dd.append(d)
                    if ('director' not in adata or len(adata['director']) == 0) and len(dd) > 0:
                        adata['director'] = dd
                    if not adata[M] and M + '_id' in anndata:
                        adata[M] = []
                        for i in range(len(res[M])):
                            if 'ann_id' in res[M][i] and int(res[M][i]['ann_id']) == anndata[M + '_id']:
                                adata[M].append(i)
                                break
                    ids[A]['ANN'].append(annid)
                    break
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
                    if int(mid) == anndata[M + '_id']:
                        adata[M].append(i)
                        break
                    i += 1
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
    print("wa.search_anime(title, year, form) if A_M == A")
    wa_anime_pages = wa.search_anime(title, year, form) if A_M == A else None
    print("wa.search_manga(title, year) if A_M == M")
    wa_manga_pages = wa.search_manga(title, year) if A_M == M else None
    print("ann.search_pages(title, year, form)")
    ann_anime_pages, ann_manga_pages, ann_rm = ann.search_pages(title, year, form)
    print("mu.search_pages(title, year) if A_M == M")
    mu_pages = mu.search_pages(title, year) if A_M == M else None
    if not mu_pages:
        print("mu.search_pages(title)")
        mu_pages = mu.search_pages(title)
    wa_rm = {}
    if wa_anime_pages and len(wa_anime_pages):
        print("wa.manga_pages_from_anime(wa_manga_pages, wa_anime_pages)")
        wa_manga_pages, wa_rm = wa.manga_pages_from_anime(wa_manga_pages, wa_anime_pages)
    if wa_manga_pages and len(wa_manga_pages):
        print("wa.anime_pages_from_manga(wa_anime_pages, wa_manga_pages)")
        wa_anime_pages = wa.anime_pages_from_manga(wa_anime_pages, wa_manga_pages)
    print("ann_pages_in_wa(ann_anime_pages, ann_manga_pages, wa_anime_pages, wa_manga_pages)")
    ann_anime_pages, ann_manga_pages, ann_rm = ann_pages_in_wa(ann_anime_pages, ann_manga_pages, wa_anime_pages,
                                                               wa_manga_pages)
    print("wp_pages_in_wa(title)")
    wp_pages = wp_pages_in_wa(title)
    print("wp.filter_page_parts(wp.manga_anime_in_page(wp_pages))")
    wp_page_parts = wp.filter_page_parts(wp.manga_anime_in_page(wp_pages))

    if not len(wp_page_parts):
        print(f"wp_pages_in_wa('{title} {M}')")
        wp_pages = wp_pages_in_wa(f"{title} {M}")
        print("wp.filter_page_parts(wp.manga_anime_in_page(wp_pages))")
        wp_page_parts = wp.filter_page_parts(wp.manga_anime_in_page(wp_pages))
    if not len(wp_page_parts):
        print(f"wp_pages_in_wa('{title.replace("ou", "o")} {M}')")
        wp_pages = wp_pages_in_wa(f"{title.replace("ou", "o")} {M}")
        print("wp.filter_page_parts(wp.manga_anime_in_page(wp_pages))")
        wp_page_parts = wp.filter_page_parts(wp.manga_anime_in_page(wp_pages))
    print("mu_pages_in_wa(mu_pages, wa_manga_pages)")
    mu_pages = mu_pages_in_wa(mu_pages, wa_manga_pages)

    # Извлечение данных из страниц
    wa_data = {}
    if wa_manga_pages and len(wa_manga_pages):
        print("{id_: wa.extraction_manga(page) for id_, page in wa_manga_pages.items()}")
        wa_data[M] = {id_: wa.extraction_manga(page) for id_, page in wa_manga_pages.items()}
    if wa_anime_pages and len(wa_anime_pages):
        print("{id_: wa.extraction_anime(page, wa_rm[id_] if id_ in wa_rm else None) "
              "for id_, page in wa_anime_pages.items()}")
        wa_data[A] = {id_: wa.extraction_anime(page, wa_rm[id_] if id_ in wa_rm else None)
                      for id_, page in wa_anime_pages.items()}
    ann_data = {}
    if ann_manga_pages and len(ann_manga_pages):
        print("{id_: ann.extraction_manga(id_, ann_xml) for id_, ann_xml in ann_manga_pages.items()}")
        ann_data[M] = {id_: ann.extraction_manga(id_, ann_xml) for id_, ann_xml in ann_manga_pages.items()}
    if ann_anime_pages and len(ann_anime_pages):
        print("{id_: ann.extraction_anime(ann_xml, ann_rm[id_] if id_ in ann_rm else None) "
              "for id_, ann_xml in ann_anime_pages.items()}")
        ann_data[A] = {id_: ann.extraction_anime(ann_xml, ann_rm[id_] if id_ in ann_rm else None)
                       for id_, ann_xml in ann_anime_pages.items()}
    print("wp.extraction_data(wp_page_parts, wp_pages) if len(wp_page_parts)")
    wp_data = wp.extraction_data(wp_page_parts, wp_pages) if len(wp_page_parts) else None
    print("{id_: mu.extraction_manga(page) for id_, page in mu_pages.items()} if mu_pages and len(mu_pages)")
    mu_data = {id_: mu.extraction_manga(page) for id_, page in mu_pages.items()} if mu_pages and len(mu_pages) else None

    # Проверка наличия наименований ANN и WP в WA: поиск и добавление отсутствующих
    # wa_id = {A: set(wa_anime_pages.keys()) if wa_anime_pages and len(wa_anime_pages) else [],
    #          M: set(wa_manga_pages.keys()) if wa_manga_pages and len(wa_manga_pages) else []}
    wa_id = {A: [int(k) for k in wa_anime_pages.keys()] if wa_anime_pages and len(wa_anime_pages) else [],
             M: [int(k) for k in wa_manga_pages.keys()] if wa_manga_pages and len(wa_manga_pages) else []}
    wa_anime_pages = {}
    wa_manga_pages = {}
    for am, anndata in ann_data.items():
        for annid, data in anndata.items():
            if (am == M and not len(wa_manga_pages)) or (am == A and not len(wa_anime_pages)) or am not in wa_data:
                wa_pages_update("ann")
            else:
                for wadata in wa_data[am].values():
                    if int(annid) == wadata['ann']:
                        break
                else:
                    if am == M and len(wa_manga_pages):
                        for wmp in wa_manga_pages.values():
                            if f"{ANNE}{M}.php?id={annid}" in wmp:
                                break
                        else:
                            wa_pages_update("ann")
                    elif am == A and len(wa_anime_pages):
                        for wap in wa_anime_pages.values():
                            if f"{SANNE}{A}.php?id={annid}" in wap:
                                break
                        else:
                            wa_pages_update("ann")
    for am, wpdata in wp_data.items():
        for wptit, data in wpdata.items():
            if (am == M and not len(wa_manga_pages)) or (am == A and not len(wa_anime_pages)) or am not in wa_data:
                wa_pages_update("wp")
            else:
                for wadata in wa_data[am].values():
                    if normal_name(wptit[:-13]) == normal_name(wadata['name_eng']):
                        break
                else:
                    if am == M and len(wa_manga_pages):
                        for wmp in wa_manga_pages.values():
                            if f"{WPE}{wptit[:-13].replace(" ", "_")}" in wmp:
                                break
                        else:
                            wa_pages_update("wp")
                    elif am == A and len(wa_anime_pages):
                        for wap in wa_anime_pages.values():
                            if f"{WPE}{wptit[:-13].replace(" ", "_")}" in wap:
                                break
                        else:
                            wa_pages_update("wp")
    wa_rm = {}
    if len(wa_anime_pages):
        print("wa.manga_pages_from_anime(wa_manga_pages, wa_anime_pages)")
        wa_manga_pages, wa_rm = wa.manga_pages_from_anime(wa_manga_pages, wa_anime_pages)
    if len(wa_manga_pages):
        print("wa.anime_pages_from_manga(wa_anime_pages, wa_manga_pages)")
        wa_anime_pages = wa.anime_pages_from_manga(wa_anime_pages, wa_manga_pages)

        # Извлечение данных из страниц
        if M not in wa_data:
            wa_data[M] = {}
        print("{id_: wa.extraction_manga(page) for id_, page in wa_manga_pages.items()}")
        wa_data[M].update({id_: wa.extraction_manga(page) for id_, page in wa_manga_pages.items()})
    if len(wa_anime_pages):
        if A not in wa_data:
            wa_data[A] = {}
        print("{id_: wa.extraction_anime(page, wa_rm[id_] if id_ in wa_rm else None) "
              "for id_, page in wa_anime_pages.items()}")
        wa_data[A].update({id_: wa.extraction_anime(page, wa_rm[id_] if id_ in wa_rm else None)
                           for id_, page in wa_anime_pages.items()})

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
