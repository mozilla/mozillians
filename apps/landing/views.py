import jingo

from django.http import HttpResponse

import logging
log = logging.getLogger('phonebook')
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)

from django_auth_ldap.backend import LDAPBackend


def about(request):
    return jingo.render(request, 'landing/about.html')


def home(request):
    # request.user.ldap_user.attrs
    try:
        log.error("ldap_user=%s" % str(dir(request.user.ldap_user)))
        log.error("username=%s" % str(request.user.username))

        log.error("_user_dn=%s" % str(request.user._get_user_dn()))
        log.error("attrs=%s" % str(request.user.ldap_user.attrs))
        log.error("keys=%s" % str(request.user.ldap_user.attrs.keys))
    except Exception, x:
        log.error(x)
        pass
    log.error("going for it")

    #u = LDAPBackend.populate_user(request.user.username)
    #log.error(u)
    return jingo.render(request, 'landing/home.html')


def handler404(request):
    return jingo.render(request, 'landing/404.html', status=404)


def handler500(request):
    return jingo.render(request, 'landing/500.html', status=500)


def robots(request):
    return HttpResponse("""User-agent: *\nDisallow: /\n""",
                        mimetype="text/plain")

def confirm_register(request):
    return jingo.render(request, 'landing/confirm_register.html',
                        dict())
