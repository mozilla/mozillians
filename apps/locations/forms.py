from django import forms

from tower import ugettext_lazy as _lazy

from locations.models import Address, Country


class AddressForm(forms.ModelForm):

    class Meta:
        # Model form stuff
        model = Address
        # Foreign key defaults to choices in a model form. Set the right
        # choices in the init method.
        fields = ('street', 'city', 'province', 'postal_code', 'country')

    def __init__(self, *args, **kwargs):
        """Add a locale-aware list of countries to the form."""

        # If we have an instance and that instance has a country, lets update
        # the intial option to be the one of the country.
        instance = kwargs.get('instance')
        if instance:
            initial = kwargs.get('initial', {})
            if instance.country:
                initial.update(country=instance.country.id)

            kwargs['initial'] = initial

        # Get our current local from keywords.
        locale = kwargs.get('locale', 'en-US')
        if kwargs.get('locale'):
            del kwargs['locale']

        super(AddressForm, self).__init__(*args, **kwargs)

        # Set the country fields to the properly localized ones.
        self.fields['country'] = forms.ChoiceField(label=_lazy(u'Country'),
                required=False, choices=([['', '--']] +
                                         Country.localized_list(locale)))

    def clean_country(self):
        """Return a country object for the country selected (None if empty)."""
        if not self.cleaned_data['country']:
            return None

        country = Country.objects.filter(id=self.cleaned_data['country'])[0]
        return country if country else None
