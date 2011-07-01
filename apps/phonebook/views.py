import logging
log = logging.getLogger('phonebook')
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)

import jingo

def profile_uid(request, userid):
    return profile(request, userid)

def profile_nickname(request, nickname):
    return profile(request, nickname)

def profile(request, person):
    log.error("hello hello %s" % request.user)
    return jingo.render(request, 'phonebook/profile.html', 
                        dict(person=person))

def edit_profile(request, person):
    return jingo.render(request, 'phonebook/edit_profile.html')

def search(request):
    return jingo.render(request, 'phonebook/search.html')

def invite(request):
    return jingo.render(request, 'phonebook/invite.html')
