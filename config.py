# COOKIE авторизации на World Art.
COOKIES_WA = {'user_login': '', 'user_password': ''}

# Параметры подключения к БД.
# DB_CONNECT = ("Сервер", "логин", "пароль", "БД")
DB_CONNECT = ("localhost", "", "", "anime_manga")

# Путь хранения микропостеров. Например: 'C:/LOCALHOST/anime_manga/microposter/'.
PATH = ''

# Shikimori-форматы anime в WA.
FORM_WA_SH = {
    'полнометражный фильм': 'movie',
    'OVA': 'ova',
    'ONA': 'ona',
    'ТВ-спэшл': 'tv_special',
    'ТВ': 'tv'
}

# WA-форматы anime в Shikimori.
FORM_SH_WA = {
    'movie': 'полнометражный фильм',
    'ova': 'OVA',
    'ona': 'ONA',
    'tv_special': 'ТВ-спэшл',
    'tv': 'ТВ'
}

# WA-форматы anime в ANN.
FORM_ANN = {
    'movie': 'полнометражный фильм',
    'OAV': 'OVA',
    'ONA': 'ONA',
    'special': 'ТВ-спэшл',
    'TV': 'ТВ'
}

# WA-форматы anime в Wikipedia.
FORM_WP = {
    'Anime film series': 'полнометражный фильм',
    'Anime television series': 'ТВ',
    'Original video animation': 'OVA'
}

# Игнорируемые жанры.
IGNORED_GENRES = {'дзёсэй', 'история', 'сёдзё', 'сёнэн', 'сэйнэн', 'Action', 'Adult', 'Cars', 'Dementia', 'Demons',
                  'Doujinshi', 'Game', 'Gender Bender', 'Gourmet', 'Harem', 'Historical', 'Josei', 'Kids', 'Mature',
                  'Military', 'Music', 'Police', 'Samurai', 'Seinen', 'Shoujo', 'Shoujo Ai', 'Shounen', 'Shounen Ai',
                  'Super Power', 'Tournament', 'Vampire', 'Work Life', 'Yaoi', 'Yuri'}

# Жанры Shikimori.
GENRES_SH = {
    'Adventure': "приключения",
    'Comedy': "комедия",
    'Drama': "драма",
    'Ecchi': "этти",
    'Erotica': "эротика",
    'Fantasy': "фэнтези",
    'Hentai': "хентай",
    'Horror': "ужасы",
    'Magic': "магия",
    'Martial Arts': "боевые искусства",
    'Mecha': "меха",
    'Mystery': "мистика",
    'Parody': "пародия",
    'Psychological': "психология",
    'Romance': "романтика",
    'School': "школа",
    'Sci-Fi': "фантастика",
    'Slice of Life': "повседневность",
    # 'Space': "космос",
    'Sports': "спорт",
    'Supernatural': "сверхъестественное",
    'Thriller': "триллер"
}

# Жанры AnimeNewsNetwork.
GENRES_ANN = {
    'adventure': 'приключения',
    'comedy': 'комедия',
    'drama': 'драма',
    'erotica': 'эротика',
    'fantasy': 'фэнтези',
    'horror': 'ужасы',
    'magic': 'магия',
    'mystery': 'мистика',
    'psychological': 'психология',
    'romance': 'романтика',
    'science fiction': 'фантастика',
    'slice of life': 'повседневность',
    'supernatural': 'сверхъестественное',
    'thriller': 'триллер'
}

# Жанры MangaUpdate.
GENRES_MU = {
    'Adventure': 'приключения',
    'Comedy': 'комедия',
    'Drama': 'драма',
    'Ecchi': 'этти',
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
