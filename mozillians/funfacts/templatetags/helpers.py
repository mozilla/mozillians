from django_jinja import library

from mozillians.funfacts.models import FunFact


@library.global_function
def random_funfact():
    """Returns random funfact or None."""

    if FunFact.objects.published().count():
        return FunFact.objects.random()
    return None
