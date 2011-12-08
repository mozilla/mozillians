from django.contrib import auth, messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

import commonware.log
from funfactory.urlresolvers import reverse
from funfactory.utils import absolutify
from tower import ugettext as _

from browserid.forms import ModalBrowserIdForm
from larper import store_assertion


log = commonware.log.getLogger('m.browserid')


@require_POST
def browserid_login(request):
    """Multi-mode BrowserID authentication form processor.

    Handles login and register browserid verification. If
    the mode is login, we are done. If the mode is register
    then we start new profile flow. Also handles corner cases.

    Login and register sasl-browserid verification steps are very similar
    and the corner cases blur the lines, so this is best as one
    url.

    We use the form from django-browserid, but since the LDAP server
    does the BrowserID auth behind the scenes, we don't use it's auth code
    nor it's views.
    """
    form = ModalBrowserIdForm(data=request.POST)
    if form.is_valid():
        assertion = form.cleaned_data['assertion']
        store_assertion(request, assertion)
        mode = form.cleaned_data['mode']
        user = auth.authenticate(request=request, assertion=assertion)
        if user:
            auth.login(request, user)
            return redirect('profile', request.user.unique_id)
        else:
            url = absolutify("%s?link=%s" % (reverse('register'), mode))
            return redirect(url)
    else:
        msg = _('Sorry, but there were problems with the info you submitted. '
                'Please review the form, correct any errors, and try again.')
        messages.warning(request, msg)
        log.warning("Form didn't validate %s" % str(request.POST))
        return redirect('home')
