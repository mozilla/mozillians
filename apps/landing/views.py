from django.shortcuts import render

from django.http import HttpResponse


def about(request):
    return render(request, 'landing/about.html')


def home(request):
    return render(request, 'landing/home.html')


# TODO: this should be served statically.
def robots(request):
    return HttpResponse("""User-agent: *\nDisallow: /\n""",
                        mimetype="text/plain")


def confirm_register(request):
    return render(request, 'landing/confirm_register.html')
