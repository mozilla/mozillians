import babel


AVAILABLE_LANGUAGES = {}
REMOVE_KEYS = ['mul', 'und', 'mis', 'zxx', 'en_US', 'en_GB']


def get_localized_language(locale):
    """Return all the available languages for a locale."""
    try:
        languages = babel.Locale(locale).languages
    except babel.UnknownLocaleError:
        languages = babel.Locale('en').languages

    for k in REMOVE_KEYS:
        if k in languages:
            del languages[k]
    return languages


LANGUAGE_REFERENCE = get_localized_language('en')


def get_translated_languages(locale):
    """This method returns all the available languages,

    localized in user's native language. If a language is not localized,
    return the equivalent translation into English.
    The available translations for each locale are stored in
    AVAILABLE_LANGUAGES for caching purposes.
    Babel internationalization utilities are used for this purpose."""

    if locale == 'en-US':
        locale = 'en'
    if locale:
        locale = locale.replace('-', '_')
    if locale not in AVAILABLE_LANGUAGES:
        try:
            local_lang = get_localized_language(locale)
        except babel.UnknownLocaleError:
            if 'en' in AVAILABLE_LANGUAGES:
                return AVAILABLE_LANGUAGES['en']
            local_lang = LANGUAGE_REFERENCE
        diff = [lc for lc in LANGUAGE_REFERENCE.keys()
                if lc not in local_lang.keys()]
        for lc in diff:
            local_lang[lc] = LANGUAGE_REFERENCE[lc]
        AVAILABLE_LANGUAGES[locale] = sorted([(key, value.capitalize())
                                             for key, value in local_lang.items()],
                                             key=lambda language: language[1])
        if AVAILABLE_LANGUAGES[locale][0][1] != '-----':
            AVAILABLE_LANGUAGES[locale].insert(0, ('', '-----'))
    return AVAILABLE_LANGUAGES[locale]
