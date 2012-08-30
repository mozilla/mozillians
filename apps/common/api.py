from django.template.loader import render_to_string

from tastypie.serializers import Serializer


class HTMLSerializer(Serializer):
    """HTML Serializer for django-tastypie."""
    formats = ['json', 'jsonp', 'xml', 'html']
    content_types = {
        'json': 'application/json',
        'jsonp': 'text/javascript',
        'xml': 'application/xml',
        'html': 'text/html',
    }

    def to_html(self, data, options=None):
        """Return /data/ to html."""
        return render_to_string('api.html', locals())
