import babel


LANGUAGE_REFERENCE = babel.Locale('en_US').languages
AVAILABLE_LANGUAGES = {}


def get_translated_languages(locale):
    if locale not in AVAILABLE_LANGUAGES:
        try:
            local_lang = babel.Locale(locale).languages
        except babel.UnknownLocaleError:
            if 'en_US' in AVAILABLE_LANGUAGES:
                return AVAILABLE_LANGUAGES['en_US']
            local_lang = LANGUAGE_REFERENCE
        diff = [lc for lc in LANGUAGE_REFERENCE.keys()
                if lc not in local_lang.keys()]
        for lc in diff:
            local_lang[lc] = LANGUAGE_REFERENCE[lc]
        AVAILABLE_LANGUAGES[locale] = sorted([(key, value.capitalize())
                                             for key, value in local_lang.items()],
                                             key=lambda language: language[1])
    return AVAILABLE_LANGUAGES[locale]
