-- Bug#673257 Registering with long email address breaks django.contrib.auth

ALTER TABLE auth_user CHANGE COLUMN username username VARCHAR(255);
ALTER TABLE auth_user CHANGE COLUMN first_name first_name VARCHAR(255);
ALTER TABLE auth_user CHANGE COLUMN last_name last_name VARCHAR(255);
ALTER TABLE auth_user CHANGE COLUMN email email VARCHAR(255);

