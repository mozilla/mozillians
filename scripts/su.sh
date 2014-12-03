#!/bin/bash

echo -n "Enter your BrowserID email: "
read USEREMAIL
U=$(cat << _EOF_
from mozillians.users.models import User, UserProfile, Vouch
\nu = User.objects.get(email="$USEREMAIL")
\nu.is_superuser = True
\nu.is_staff = True
\nu.save()

\np = UserProfile.objects.get(user=u)
\np.vouch(None, description='su vouch 1', autovouch=True)
\np.vouch(None, description='su vouch 2', autovouch=True)
\np.vouch(None, description='su vouch 3', autovouch=True)
\np.vouch(None, description='su vouch 4', autovouch=True)
\np.vouch(None, description='su vouch 5', autovouch=True)
\np.save()

_EOF_
)

echo -e $U | ./manage.py shell #2>1 /dev/null
echo "Done!"
