from __future__ import with_statement, unicode_literals

from django.core.files.base import ContentFile
from django.utils.safestring import mark_safe

import base64

from compressor.css import CssCompressor
from compressor.js import JsCompressor
from hashlib import sha384


def _compute_sri_value(content):
    sri_hash = sha384(content.encode('utf-8')).digest()
    sri_value = base64.b64encode(sri_hash)
    return 'sha384-{}'.format(sri_value)


class SRIMixin(object):

    def output_file(self, mode, content, forced=False, basename=None):
        """
        The output method that saves the content to a file and renders
        the appropriate template with the file's URL.
        """
        new_filepath = self.get_filepath(content, basename=basename)
        if not self.storage.exists(new_filepath) or forced:
            self.storage.save(new_filepath, ContentFile(content.encode(self.charset)))
        url = mark_safe(self.storage.url(new_filepath))
        context = {
            'url': url,
            'sri': _compute_sri_value(content)
        }
        return self.render_output(mode, context)

    def output_inline(self, mode, content, forced=False, basename=None):
        """
        The output method that directly returns the content for inline
        display.
        """
        context = {
            'content': content,
            'sri': _compute_sri_value(content)
        }
        return self.render_output(mode, context)


class SRIJsCompressor(SRIMixin, JsCompressor):
    pass


class SRICssCompressor(SRIMixin, CssCompressor):
    pass
