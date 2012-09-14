#!/bin/bash

echo -n "Enter your BrowserID email: "
read USEREMAIL
U=$(cat << _EOF_
from apps.users.models import User, UserProfile
\nu = User.objects.get(email="$USEREMAIL")
\nu.is_superuser = True
\nu.is_staff = True
\nu.save()

\np = UserProfile.objects.get(user=u)
\np.is_vouched = True
\np.save()

_EOF_
)

echo -e $U | ./manage.py shell #2>1 /dev/null
echo "Done!"
