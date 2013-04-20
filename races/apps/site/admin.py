'''
Created on Apr 15, 2013

@author: steve
'''
from django.contrib import admin
from races.apps.site.models import Club, RaceCourse, Race

admin.site.register(Club)

admin.site.register(RaceCourse)

admin.site.register(Race)