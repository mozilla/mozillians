from django.contrib.auth.models import User

import autocomplete_light

from mozillians.users.models import UserProfile


class UserProfileAutocomplete(autocomplete_light.AutocompleteModelBase):
    """Any user profile"""
    search_fields = ['full_name', 'user__email', 'user__username']
    choices = UserProfile.objects.all()


autocomplete_light.register(UserProfile, UserProfileAutocomplete,
                            name='UserProfiles')


class VouchedUserProfileAutocomplete(autocomplete_light.AutocompleteModelBase):
    """Only vouched user profiles"""
    search_fields = ['full_name', 'user__email', 'user__username']
    choices = UserProfile.objects.vouched()


autocomplete_light.register(UserProfile, VouchedUserProfileAutocomplete,
                            name='VouchedUserProfiles')


class VouchedUserAutocomplete(autocomplete_light.AutocompleteModelBase):
    """Vouched users"""
    search_fields = ['userprofile__full_name', 'email']
    choices = (User.objects.exclude(userprofile__full_name='')
               .filter(userprofile__is_vouched=True))

autocomplete_light.register(User, VouchedUserAutocomplete,
                            name='VouchedUsers')
