import csv
from datetime import datetime, timedelta

from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseRedirect

import autocomplete_light
from celery.task.sets import TaskSet
from functools import update_wrapper
from sorl.thumbnail.admin import AdminImageMixin

import mozillians.users.tasks
from mozillians.users.cron import index_all_profiles
from mozillians.users.models import (COUNTRIES, PUBLIC, UserProfile,
                                     UsernameBlacklist)


admin.site.unregister(User)
admin.site.unregister(Group)

Q_PUBLIC_PROFILES = Q()
for field in UserProfile.privacy_fields():
    key = 'userprofile__privacy_%s' % field
    Q_PUBLIC_PROFILES |= Q(**{key: PUBLIC})


def export_as_csv_action(description=None, fields=None, exclude=None,
                         header=True):
    """
    This function returns an export csv action
    'fields' and 'exclude' work like in django ModelForm
    'header' is whether or not to output the column names as the first row

    Based on snippet http://djangosnippets.org/snippets/2020/
    """

    def export_as_csv(modeladmin, request, queryset):
        """
        Generic csv export admin action.
        based on http://djangosnippets.org/snippets/1697/
        """
        opts = modeladmin.model._meta
        field_names = set([field.name for field in opts.fields])
        if fields:
            fieldset = set(fields)
            field_names = field_names & fieldset
        elif exclude:
            excludeset = set(exclude)
            field_names = field_names - excludeset

        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = ('attachment; filename=%s.csv' %
                                           unicode(opts).replace('.', '_'))

        writer = csv.writer(response, delimiter=';')
        if header:
            writer.writerow(list(field_names))
        for obj in queryset:
            writer.writerow([unicode(getattr(obj, field)).encode('utf-8')
                             for field in field_names])
        return response

    export_as_csv.short_description = (description or 'Export to CSV file')
    return export_as_csv


def subscribe_to_basket_action():
    """Subscribe to Basket action."""

    def subscribe_to_basket(modeladmin, request, queryset):
        """Subscribe to Basket or update details of already subscribed."""
        ts = [(mozillians.users.tasks.update_basket_task
               .subtask(args=[user.userprofile.id]))
              for user in queryset]
        TaskSet(ts).apply_async()
        messages.success(request, 'Basket update started.')
    subscribe_to_basket.short_description = 'Subscribe to or Update Basket'
    return subscribe_to_basket


def unsubscribe_from_basket_action():
    """Unsubscribe from Basket action."""

    def unsubscribe_from_basket(modeladmin, request, queryset):
        """Unsubscribe from Basket."""
        ts = [(mozillians.users.tasks.remove_from_basket_task
               .subtask(user.email, user.userprofile.basket_token))
              for user in queryset]
        TaskSet(ts).apply_async()
        messages.success(request, 'Basket update started.')
    unsubscribe_from_basket.short_description = 'Unsubscribe from Basket'
    return unsubscribe_from_basket


class SuperUserFilter(SimpleListFilter):
    """Admin filter for superusers."""
    title = 'has access to admin interface'
    parameter_name = 'superuser'

    def lookups(self, request, model_admin):
        return (('False', 'No'),
                ('True', 'Yes'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        value = self.value() == 'True'
        return queryset.filter(is_staff=value)


class PublicProfileFilter(SimpleListFilter):
    """Admin filter for public profiles."""
    title = 'public profile'
    parameter_name = 'public_profile'

    def lookups(self, request, model_admin):
        return (('False', 'No'),
                ('True', 'Yes'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        if self.value() == 'True':
            return queryset.filter(Q_PUBLIC_PROFILES)

        return queryset.exclude(Q_PUBLIC_PROFILES)


class CompleteProfileFilter(SimpleListFilter):
    """Admin filter for complete profiles."""
    title = 'complete profile'
    parameter_name = 'complete_profile'

    def lookups(self, request, model_admin):
        return (('False', 'Incomplete'),
                ('True', 'Complete'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        elif self.value() == 'True':
            return queryset.exclude(userprofile__full_name='')
        else:
            return queryset.filter(userprofile__full_name='')


class DateJoinedFilter(SimpleListFilter):
    """Admin filter for date joined."""
    title = 'date joined'
    parameter_name = 'date_joined'

    def lookups(self, request, model_admin):

        return map(lambda x: (str(x.year), x.year),
                   User.objects.dates('date_joined', 'year'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        else:
            return queryset.filter(date_joined__year=self.value())
        return queryset


class LastLoginFilter(SimpleListFilter):
    """Admin filter for last login."""
    title = 'last login'
    parameter_name = 'last_login'

    def lookups(self, request, model_admin):
        return (('<6', 'Less than 6 months'),
                ('>6', 'Between 6 and 12 months'),
                ('>12', 'More than a year'))

    def queryset(self, request, queryset):
        half_year = datetime.today() - timedelta(days=180)
        full_year = datetime.today() - timedelta(days=360)

        if self.value() == '<6':
            return queryset.filter(last_login__gte=half_year)
        elif self.value() == '>6':
            return queryset.filter(last_login__lt=half_year,
                                   last_login__gt=full_year)
        elif self.value() == '>12':
            return queryset.filter(last_login__lt=full_year)
        return queryset


class UserProfileInline(AdminImageMixin, admin.StackedInline):
    """UserProfile Inline model for UserAdmin."""
    model = UserProfile
    readonly_fields = ['date_vouched', 'vouched_by', 'basket_token']
    form = autocomplete_light.modelform_factory(UserProfile)


class UserAdmin(UserAdmin):
    """User Admin."""
    inlines = [UserProfileInline]
    search_fields = ['userprofile__full_name', 'email', 'username',
                     'userprofile__ircname']
    list_filter = ['userprofile__is_vouched', DateJoinedFilter,
                   LastLoginFilter, SuperUserFilter, CompleteProfileFilter,
                   PublicProfileFilter]
    save_on_top = True
    list_display = ['full_name', 'email', 'username', 'country', 'is_vouched',
                    'vouched_by', 'number_of_vouchees']
    list_display_links = ['full_name', 'email', 'username']
    actions = [export_as_csv_action(fields=('username', 'email'), header=True),
               subscribe_to_basket_action(), unsubscribe_from_basket_action()]

    def queryset(self, request):
        qs = super(UserAdmin, self).queryset(request)
        qs = qs.annotate(Count('userprofile__vouchees'))
        return qs

    def country(self, obj):
        return COUNTRIES.get(obj.userprofile.country, '')
    country.admin_order_field = 'userprofile__country'

    def is_vouched(self, obj):
        return obj.userprofile.is_vouched
    is_vouched.boolean = True
    is_vouched.admin_order_field = 'userprofile__is_vouched'

    def vouched_by(self, obj):
        voucher = obj.userprofile.vouched_by
        voucher_url = reverse('admin:auth_user_change', args=[voucher.id])
        return '<a href="%s">%s</a>' % (voucher_url, voucher)
    vouched_by.admin_order_field = 'userprofile__vouched_by'
    vouched_by.allow_tags = True

    def number_of_vouchees(self, obj):
        """Return the number of vouchees for obj."""
        return obj.userprofile.vouchees.count()
    number_of_vouchees.admin_order_field = 'userprofile__vouchees__count'

    def index_profiles(self, request):
        """Fire an Elastic Search Index Profiles task."""
        index_all_profiles()
        messages.success(request, 'Profile indexing started.')
        return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

    def get_actions(self, request):
        """Return bulk actions for UserAdmin without bulk delete."""
        actions = super(UserAdmin, self).get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def get_urls(self):
        """Return custom and UserAdmin urls."""

        def wrap(view):

            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        urls = super(UserAdmin, self).get_urls()
        my_urls = patterns('',
                           url(r'index_profiles', wrap(self.index_profiles),
                               name='users_index_profiles'))
        return my_urls + urls

    def full_name(self, obj):
        return obj.userprofile.full_name

admin.site.register(User, UserAdmin)


class UsernameBlacklistAdmin(admin.ModelAdmin):
    """UsernameBlacklist Admin."""
    save_on_top = True
    search_fields = ['value']
    list_filter = ['is_regex']
    list_display = ['value', 'is_regex']

admin.site.register(UsernameBlacklist, UsernameBlacklistAdmin)
