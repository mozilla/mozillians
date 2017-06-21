from haystack import indexes

from mozillians.groups.models import GroupMembership
from mozillians.users.models import UserProfile


class UserProfileIndex(indexes.SearchIndex, indexes.Indexable):
    """User Profile Search Index."""
    # Primary field of the index
    text = indexes.CharField(document=True, use_template=True)
    # profile information
    full_name = indexes.CharField(model_attr='full_name')
    privacy_full_name = indexes.IntegerField(model_attr='privacy_full_name')
    email = indexes.CharField(model_attr='email')
    privacy_email = indexes.IntegerField(model_attr='privacy_email')
    ircname = indexes.CharField(model_attr='ircname')
    privacy_ircname = indexes.IntegerField(model_attr='privacy_ircname')
    bio = indexes.CharField(model_attr='bio')
    privacy_bio = indexes.IntegerField(model_attr='privacy_bio')
    # location information - related fields
    country = indexes.CharField(model_attr='country__name', null=True)
    privacy_country = indexes.IntegerField(model_attr='privacy_country')
    region = indexes.CharField(model_attr='region__name', null=True)
    privacy_region = indexes.IntegerField(model_attr='privacy_region')
    city = indexes.CharField(model_attr='city__name', null=True)
    privacy_city = indexes.IntegerField(model_attr='privacy_city')
    # skills/groups/languages - m2m related fields
    skills = indexes.MultiValueField()
    privacy_skills = indexes.IntegerField(model_attr='privacy_skills')
    languages = indexes.MultiValueField()
    privacy_languages = indexes.IntegerField(model_attr='privacy_languages')
    groups = indexes.MultiValueField()
    privacy_groups = indexes.IntegerField(model_attr='privacy_groups')

    # Django's username does not have privacy level
    username = indexes.CharField(model_attr='user__username')

    def get_model(self):
        return UserProfile

    def prepare_skills(self, obj):
        return [skill.name for skill in obj.skills.all()]

    def prepare_languages(self, obj):
        return [language.get_code_display() for language in obj.languages.all()]

    def prepare_groups(self, obj):
        return [group.name for group in obj.groups.filter(
            groupmembership__status=GroupMembership.MEMBER)]

    def index_queryset(self, using=None):
        """Exclude incomplete profiles from indexing."""
        return self.get_model().objects.complete()
