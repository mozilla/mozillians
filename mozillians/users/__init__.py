from django.apps import AppConfig

import babel


default_app_config = 'mozillians.users.UserConfig'


class UserConfig(AppConfig):
    name = 'mozillians.users'


AVAILABLE_LANGUAGES = {}
REMOVE_LANGS = ['art', 'cpe', 'cpf', 'cpp', 'de_AT', 'de_CH',
                'mul', 'und', 'mis', 'zxx', 'en_US', 'en_GB', 'en_AU', 'en_CA',
                'fr_CA', 'fr_CH']


def get_languages_for_locale(locale):
    """This method returns available languages localized in locale.

    If a language cannnot be localized, return REFERENCE_LANGUAGE.
    Translated dictionaries get cached in AVAILABLE_LANGUAGES.

    We use Babel to get translated language names.

    """
    # Babel uses _ instead of - for locales. E.g. 'en_US' instead of
    # 'en-US'
    locale = locale.replace('-', '_')
    if locale not in AVAILABLE_LANGUAGES:
        try:
            local_lang = babel.Locale(locale).languages
        except babel.UnknownLocaleError:
            return AVAILABLE_LANGUAGES['en']

        # If a translation is missing, add an untranslated entry from
        # the REFERENCE_LANGUAGE
        diff = [lc for lc in REFERENCE_LANGUAGE.keys()
                if lc not in local_lang.keys()]
        for lc in diff:
            local_lang[lc] = REFERENCE_LANGUAGE[lc]

        # Remove unwanted and testing languages.
        map(local_lang.pop, REMOVE_LANGS)

        # Sort based on language name.
        local_lang = sorted([(key, value.capitalize())
                             for key, value in local_lang.items()],
                            key=lambda language: language[1])

        AVAILABLE_LANGUAGES[locale] = local_lang
    return AVAILABLE_LANGUAGES[locale]


REFERENCE_LANGUAGE = babel.Locale('en').languages
# Add 'en' to AVAILABLE_LANGUAGES
get_languages_for_locale('en')
