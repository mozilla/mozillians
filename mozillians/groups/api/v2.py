from django.shortcuts import get_object_or_404

import django_filters
from funfactory.urlresolvers import reverse
from rest_framework import viewsets, serializers
from rest_framework.response import Response

from mozillians.common.helpers import absolutify
from mozillians.groups.models import Group, GroupMembership, Skill
from mozillians.users.models import UserProfile


class GroupMemberSerializer(serializers.HyperlinkedModelSerializer):
    privacy = serializers.CharField(source='get_privacy_groups_display')
    username = serializers.Field(source='user.username')

    class Meta:
        model = UserProfile
        fields = ('privacy', 'username', '_url')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    member_count = serializers.Field()
    url = serializers.SerializerMethodField('get_url')

    class Meta:
        model = Group
        fields = ('id', 'url', 'name', 'member_count', '_url')

    def get_url(self, obj):
        return absolutify(reverse('groups:show_group', kwargs={'url': obj.url}))


class GroupDetailedSerializer(GroupSerializer):
    members = GroupMemberSerializer(many=True, source='_members')
    curator = serializers.SerializerMethodField('get_curator')

    class Meta:
        # The curator field is only listed here for compatibility reasons
        # The curators field returns all the curators of a group
        model = Group
        fields = ('id', 'name', 'description', 'curator', 'curators',
                  'irc_channel', 'website', 'wiki',
                  'members_can_leave', 'accepting_new_members',
                  'new_member_criteria', 'functional_area', 'members', 'url')

    def get_curator(self, obj):
        return obj.curators.all().first()


class SkillSerializer(serializers.HyperlinkedModelSerializer):
    member_count = serializers.Field()
    url = serializers.SerializerMethodField('get_url')

    class Meta:
        model = Skill
        fields = ('id', 'url', 'name', 'member_count', '_url')

    def get_url(self, obj):
        return absolutify(reverse('groups:show_skill', kwargs={'url': obj.url}))


class SkillDetailedSerializer(SkillSerializer):
    members = GroupMemberSerializer(many=True, source='_members')

    class Meta:
        model = Skill
        fields = ('id', 'name', 'members', 'url')


class GroupFilter(django_filters.FilterSet):
    curator = django_filters.MethodFilter(action='filter_curator')

    class Meta:
        model = Group
        fields = ('name', 'functional_area', 'curators', 'curator',
                  'members_can_leave', 'accepting_new_members',)

    def filter_curator(self, queryset, value):
        return queryset.filter(curators=value)


class SkillFilter(django_filters.FilterSet):

    class Meta:
        model = Skill
        fields = ('name',)


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Returns a list of Mozillians groups respecting authorization
    levels and privacy settings.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    ordering = 'name'
    ordering_fields = ('name', 'member_count')
    filter_class = GroupFilter

    def get_queryset(self):
        queryset = Group.objects.filter(visible=True)
        return queryset

    def retrieve(self, request, pk):
        group = get_object_or_404(self.get_queryset(), pk=pk)

        # Exclude members in 'pending' state
        group._members = group.members.filter(privacy_groups__gte=self.request.privacy_level,
                                              groupmembership__status=GroupMembership.MEMBER)
        serializer = GroupDetailedSerializer(group, context={'request': self.request})
        return Response(serializer.data)


class SkillViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Returns a list of Mozillians skills respecting authorization
    levels and privacy settings.
    """
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    ordering_fields = ('name',)
    filter_class = SkillFilter

    def retrieve(self, request, pk):
        skill = get_object_or_404(self.queryset, pk=pk)
        skill._members = skill.members.filter(privacy_groups__gte=self.request.privacy_level)
        serializer = SkillDetailedSerializer(skill, context={'request': self.request})
        return Response(serializer.data)
