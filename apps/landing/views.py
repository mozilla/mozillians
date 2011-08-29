import jingo

from django.http import HttpResponse


def about(request):
    return jingo.render(request, 'landing/about.html')


def home(request):
    return jingo.render(request, 'landing/home.html')


def robots(request):
    return HttpResponse("""User-agent: *\nDisallow: /\n""",
                        mimetype="text/plain")


def confirm_register(request):
    return jingo.render(request, 'landing/confirm_register.html',
                        dict())
