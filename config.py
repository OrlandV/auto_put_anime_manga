# COOKIE авторизации на World Art.
COOKIES_WA = {'user_login': '', 'user_password': ''}

# Параметры подключения к БД.
# DB_CONNECT = ("Сервер", "логин", "пароль", "БД")
DB_CONNECT = ("localhost", "", "", "anime_manga")

# Путь хранения микропостеров. Например: 'C:/LOCALHOST/anime_manga/microposter/'.
PATH = ''

# WA-форматы anime в ANN.
FORM_ANN = {
    'movie': 'полнометражный фильм',
    'OAV': 'OVA',
    'ONA': 'ONA',
    'TV': 'ТВ'
}

# WA-форматы anime в Wikipedia.
FORM_WP = {
    'Anime film series': 'полнометражный фильм',
    'Anime television series': 'ТВ',
    'Original video animation': 'OVA'
}

# Игнорируемые жанры.
IGNORED_GENRES = {'дзёсэй', 'сёдзё', 'сёнэн', 'сэйнэн', 'Action', 'Adult', 'Doujinshi', 'Gender Bender', 'Historical',
                  'Josei', 'Mature', 'Seinen', 'Shoujo', 'Shoujo Ai', 'Shounen', 'Shounen Ai', 'Yaoi', 'Yuri'}

# Жанры AnimeNewsNetwork.
GENRES_ANN = {
    'adventure': 'приключения',
    'comedy': 'комедия',
    'drama': 'драма',
    'erotica': 'эротика',
    'fantasy': 'фэнтези',
    'horror': 'ужасы',
    'psychological': 'психология',
    'romance': 'романтика',
    'science fiction': 'фантастика',
    'slice of life': 'повседневность',
    'supernatural': 'сверхъестественное'
}

# Жанры MangaUpdate.
GENRES_MU = {
    'Adventure': 'приключения',
    'Comedy': 'комедия',
    'Drama': 'драма',
    'Fantasy': 'фэнтези',
    'Hentai': 'эротика',
    'Horror': 'ужасы',
    'Martial Arts': 'боевые искусства',
    'Mecha': 'меха',
    'Mystery': 'мистика',
    'Psychological': 'психология',
    'Romance': 'романтика',
    'School Life': 'школа',
    'Sci-fi': 'фантастика',
    'Slice of Life': 'повседневность',
    'Sports': 'спорт',
    'Supernatural': 'сверхъестественное',
    'Tragedy': 'трагедия'
}

# Периодичность издания в наименовании.
FREQUENCY = {
    'Monthly': 'Gekkan',
    'Weekly': 'Shuukan'
}


def frequency(name: str) -> str:
    """
    Замена английских периодических частей наименований на ромадзи.
    :param name: Наименование.
    :return: Исправленное наименование.
    """
    for key in FREQUENCY.keys():
        if key in name:
            return name.replace(key, FREQUENCY[key])
    return name
