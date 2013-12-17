import babel


LANGUAGE_REFERENCE = babel.Locale('en_US').languages
AVAILABLE_LANGUAGES = {}


def get_translated_languages(locale):
    if locale not in AVAILABLE_LANGUAGES:
        local_lang = babel.Locale(locale).languages
        diff = [lc for lc in LANGUAGE_REFERENCE.keys()
                if lc not in local_lang.keys()]
        for lc in diff:
            local_lang[lc] = LANGUAGE_REFERENCE[lc]
        AVAILABLE_LANGUAGES[locale] = sorted([(key, value) for key, value in
                                             local_lang.items()],
                                             key=lambda language: language[1])
    return AVAILABLE_LANGUAGES[locale]
