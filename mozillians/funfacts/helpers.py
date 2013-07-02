from jingo import register

from models import FunFact


@register.function
def random_funfact():
    """Returns random funfact or None."""
    if FunFact.objects.published().count():
        return FunFact.objects.random()
    return None
