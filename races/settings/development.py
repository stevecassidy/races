from races.settings.base import *

DATABASES['default']['NAME'] = 'races_development'

SOCIAL_AUTH_TWITTER_KEY = 'gx3LnhtWJyFbyH3bt6wR18u2j'
SOCIAL_AUTH_TWITTER_SECRET = 'SQTGvdCnhopWW6nQiCB0GozOrQSB9dvBESjif6D5xq0FkVg2gM'

SOCIAL_AUTH_STRAVA_KEY = '5805'
SOCIAL_AUTH_STRAVA_SECRET = '518be609d5f852ef1bbb64d2017afc1a5b8c71f2'

# test.cabici.net config, main site is different
SOCIAL_AUTH_FACEBOOK_KEY = '212693232435594'
SOCIAL_AUTH_FACEBOOK_SECRET = '01acd83d40e996f60386f9a87454b04c'


# email to the console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
