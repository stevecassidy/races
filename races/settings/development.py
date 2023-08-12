#!/usr/bin/python
#
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

## django-anymail configuration
#ANYMAIL = {
#    "MAILGUN_API_KEY": 'key-579a20de44b97c7dd72e13be867acb70',
#    "MAILGUN_SENDER_DOMAIN": 'mail.cabici.net'
#}
#EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"


#GEOPOSITION_GOOGLE_MAPS_API_KEY = 'AIzaSyDnUgACSI5LnSOS5hDsR-iWiZ5ARzur_Bs'
GEOPOSITION_GOOGLE_MAPS_API_KEY = 'AIzaSyCs0yGI4aREzy8Ej3zuulAsoPKtXBiSXRM'
GOOGLE_MAPS_API_KEY = GEOPOSITION_GOOGLE_MAPS_API_KEY



PINAX_WEBANALYTICS_SETTINGS = {
    "google": {
        1: "UA-41522408-1", # production
    },
}
