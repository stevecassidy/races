'''
Created on Apr 15, 2013

@author: steve
'''
from django.contrib import admin
from django import forms
from races.apps.site.models import Club, RaceCourse, Race

admin.site.register(Club)

admin.site.register(Race)



class RaceCourseAdmin(admin.ModelAdmin):
    pass

admin.site.register(RaceCourse, RaceCourseAdmin)