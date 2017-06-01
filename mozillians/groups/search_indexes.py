from haystack import indexes

from mozillians.groups.models import Group


class GroupIndex(indexes.SearchIndex, indexes.Indexable):
    """User Profile Search Index."""
    # Primary field of the index
    text = indexes.CharField(document=True, use_template=True)
    # Add the fields to index
    name = indexes.CharField(model_attr='name')
    wiki = indexes.CharField(model_attr='wiki')
    description = indexes.CharField(model_attr='description')
    visible = indexes.CharField(model_attr='visible')

    def get_model(self):
        return Group
