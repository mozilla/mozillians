from django.conf import settings

from tastypie import paginator


class Paginator(paginator.Paginator):
    """Paginator with a hard limit on results per page."""

    def get_limit(self):
        """Determines the proper maximum number of results to return.

        Overrides tastypie.paginator.Paginator class to provide a hard
        limit on number of results per page. Defaults to 500 results,
        can be adjusted through HARD_API_LIMIT_PER_PAGE variable in
        settings.

        This should be replaced with 'max_limit' tastypie.Resource
        attribute when we upgrade to tastypie >= 0.9.12.

        """
        hard_limit = getattr(settings, 'HARD_API_LIMIT_PER_PAGE', 500)
        return min(super(Paginator, self).get_limit(), hard_limit)

    def get_offset(self):
        """Determines the proper starting offset of results to return.

        Returns minimum value of offset as calculated by
        tastypie.paginator.Paginator and total objects to prevent
        Elastic Search crashes and timeouts.
        """
        return min(super(Paginator, self).get_offset(), self.get_count())
