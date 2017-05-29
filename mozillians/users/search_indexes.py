from haystack import indexes

from mozillians.users.models import UserProfile


class UserProfileIndex(indexes.SearchIndex, indexes.Indexable):
    """User Profile Search Index."""
    # Primary field of the index
    text = indexes.CharField(document=True, use_template=True)
    # Add the fields to index along with their respected privacy level
    full_name = indexes.CharField(model_attr='full_name')
    privacy_full_name = indexes.IntegerField(model_attr='privacy_full_name')

    email = indexes.CharField(model_attr='email')
    privacy_email = indexes.IntegerField(model_attr='privacy_email')

    ircname = indexes.CharField(model_attr='ircname')
    privacy_ircname = indexes.IntegerField(model_attr='privacy_ircname')

    bio = indexes.CharField(model_attr='bio')
    privacy_bio = indexes.IntegerField(model_attr='privacy_bio')

    # Django's username does not have privacy level
    username = indexes.CharField()

    def get_model(self):
        return UserProfile

    def prepare_username(self, obj):
        """Prepare the value of the foreign key for indexing."""
        return obj.user.username
