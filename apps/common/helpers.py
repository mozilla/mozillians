import logging

from django.conf import settings
from django.template import Context
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from jingo import register
from sorl.thumbnail import get_thumbnail

from apps.users.models import PUBLIC

logger = logging.getLogger('common.helpers')


@register.function
def thumbnail(source, *args, **kwargs):
    """Wraps sorl thumbnail with an additional 'default' keyword."""

    # Templates should never return an exception
    try:
        if not source.path:
            source = kwargs.get('default')
        return get_thumbnail(source, *args, **kwargs)
    except Exception as e:
        logger.error('Thumbnail had Exception: %s' % e)
        source = getattr(settings, 'DEFAULT_IMAGE_SRC')
        return get_thumbnail(source, *args, **kwargs)


@register.function
def field_with_attrs(bfield, **kwargs):
    """Allows templates to dynamically add html attributes to bound
    fields from django forms.

    Copied from bedrock.
    """
    bfield.field.widget.attrs.update(kwargs)
    return bfield


@register.function
def bootstrap(element):
    """Renders bootstrap forms in jinja2.

    Takes an element that is either a field or an entire form and
    renders the appropriate bootstrap elements.
    """
    element_type = element.__class__.__name__.lower()
    if element_type == 'boundfield':
        template = get_template("bootstrapform/field.html")
        context = Context({'field': element})
    else:
        template = get_template("bootstrapform/form.html")
        context = Context({'form': element})

    return mark_safe(template.render(context))


@register.function
def get_privacy_level(user):
    """Return privacy level user."""
    if not user.is_authenticated():
        return PUBLIC
    return user.userprofile.level
