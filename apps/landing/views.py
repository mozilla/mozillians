import jingo

from django.http import HttpResponse


def about(request):
    return jingo.render(request, 'landing/about.html')


def home(request):
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
