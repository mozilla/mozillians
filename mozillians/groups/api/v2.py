from django.shortcuts import get_object_or_404

import django_filters
from rest_framework import viewsets, serializers
from rest_framework.response import Response

from mozillians.groups.models import Group, Skill
from mozillians.users.models import UserProfile


class GroupMemberSerializer(serializers.HyperlinkedModelSerializer):
    privacy = serializers.CharField(source='get_privacy_groups_display')
    username = serializers.Field(source='user.username')

    class Meta:
        model = UserProfile
        fields = ('privacy', 'username')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    member_count = serializers.Field()

    class Meta:
        model = Group
        fields = ('name', 'member_count')


class GroupDetailedSerializer(GroupSerializer):
    members = GroupMemberSerializer(many=True, source='_members')

    class Meta:
        model = Group
        fields = ('name', 'description', 'curator',
                  'irc_channel', 'website', 'wiki',
                  'members_can_leave', 'accepting_new_members',
                  'new_member_criteria', 'functional_area', 'members',)


class SkillSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Skill
        fields = ('url', 'name')


class GroupFilter(django_filters.FilterSet):
    curator = django_filters.CharFilter()

    class Meta:
        model = Group
        fields = ('name', 'functional_area', 'curator',
                  'members_can_leave', 'accepting_new_members',)


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
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
        group._members = group.members.filter(privacy_groups__gte=self.request.privacy_level)
        serializer = GroupDetailedSerializer(group)
        return Response(serializer.data)


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    ordering_fields = ('name',)

    def get_queryset(self):
        queryset = Skill.objects.filter(visible=True)
        return queryset
