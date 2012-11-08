from django.conf import settings

from tastypie import paginator
from tastypie.exceptions import BadRequest


class Paginator(paginator.Paginator):
    """Paginator with a hard limit on results per page.

    Overrides tastypie.paginator.Paginator class to provide a hard
    limit on number of results per page. Defaults to 500 results, can
    be adjusted through HARD_API_LIMIT_PER_PAGE variable in settings.

    This should be replaced with 'max_limit' tastypie.Resource
    attribute when we upgrade to tastypie >= 0.9.12.
    """

    def get_limit(self):
        """
        Determines the proper maximum number of results to return.

        In order of importance, it will use:

            * The minimum between user-requested ``limit``
              from the GET parameters, if
              specified and HARD_API_LIMIT_PER_PAGE
            * The object-level ``limit`` if specified.
            * ``settings.API_LIMIT_PER_PAGE`` if specified.

        Default is 20 per page.
        """
        limit = getattr(settings, 'API_LIMIT_PER_PAGE', 20)
        hard_limit = getattr(settings, 'HARD_API_LIMIT_PER_PAGE', 500)

        if 'limit' in self.request_data:
            limit = self.request_data['limit']
        elif self.limit is not None:
            limit = self.limit

        try:
            limit = int(limit)
        except ValueError:
            raise BadRequest("Invalid limit '%s' provided. Please provide a "
                             "positive integer.")

        if limit < 0:
            raise BadRequest("Invalid limit '%s' provided. Please provide "
                             "an integer >= 0.")

        limit = min(limit, hard_limit)

        return limit

    def get_offset(self):
        """
        Determines the proper starting offset of results to return.

        It attempst to use the user-provided ``offset`` from the GET
        parameters, if specified. If user provided ``offset`` is
        larger than the total number of objects in the database, then
        is total number is returned to avoid ES crashes (related bug
        809669).

        Otherwise, it falls back to the object-level ``offset``.

        Default is 0.
        """
        offset = self.offset

        if 'offset' in self.request_data:
            offset = self.request_data['offset']

        try:
            offset = int(offset)
        except ValueError:
            raise BadRequest("Invalid offset '%s' provided. "
                             "Please provide an integer.")

        if offset < 0:
            raise BadRequest("Invalid offset '%s' provided. "
                             "Please provide an integer >= 0.")

        offset = min(self.get_count(), offset)

        return offset
