from haystack import indexes

from mozillians.users.models import UserProfile


class PublicUserIndex(indexes.SearchIndex, indexes.Indexable):
    """Public index for UserProfiles."""

    # primary field for search
    text = indexes.CharField(document=True, use_template=True)
    full_name = indexes.CharField(model_attr='full_name')
    ircname = indexes.CharField(model_attr='ircname')
    email = indexes.CharField(model_attr='user__email')

    def get_model(self):
        """Return the model of the index."""
        return UserProfile

    def index_queryset(self, using=None):
        """Filter out certain profiles from the index."""

        # Filter only public and complete profiles
        return self.get_model().objects.complete().public()
