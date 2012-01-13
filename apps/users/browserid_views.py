from django.conf import settings
from django.contrib import auth
from django.http import HttpResponseRedirect, HttpResponse
from django.views.decorators.http import require_POST

from django_browserid.forms import BrowserIDForm
from django_browserid.auth import get_audience

from django.views.decorators.csrf import csrf_exempt

from funfactory.urlresolvers import reverse

from django.shortcuts import redirect

'''
This view exists because the way django_browserid does it automatically
is not ideal.

TODO: fork django_browserid and use a class based view system so you can
sublcass and customize without borking everything
'''



@require_POST
def verify(request, redirect_field_name=auth.REDIRECT_FIELD_NAME):
    """Process browserid assertions."""
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    if not redirect_to:
        redirect_to = getattr(settings, 'LOGIN_REDIRECT_URL', '/')
    redirect_to_failure = getattr(settings, 'LOGIN_REDIRECT_URL_FAILURE', '/')
    form = BrowserIDForm(data=request.POST)
    if form.is_valid():
        assertion = form.cleaned_data['assertion']
        user = auth.authenticate(assertion=assertion,
                                 audience=get_audience(request))
        if user is not None and user.is_active:
            if user.get_profile().is_complete():
                auth.login(request, user)
                return HttpResponseRedirect(redirect_to)
            else:
                _store_user_in_session(request,assertion,get_audience(request))
                return redirect(reverse('register'))
    return HttpResponseRedirect(redirect_to_failure)

def _store_user_in_session(request, assertion, audience):
    '''
    Stores user in session.

    Stores user info in session to be pulled out in registration view
    '''
    request.session['assertion'] = assertion
    request.session['audience'] = audience
