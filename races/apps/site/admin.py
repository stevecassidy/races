'''
Created on Apr 15, 2013

@author: steve
'''
from django.contrib import admin
from django import forms
from races.apps.site.models import Club, RaceCourse, Race

admin.site.register(Club)


class RaceAdmin(admin.ModelAdmin):
    
    model = Race
    date_hierarchy = 'date'
    list_display = ['date', 'club', 'title']
    list_filter = ['club', 'location']
    class Meta:
        pass

admin.site.register(Race, RaceAdmin)

class RaceCourseAdmin(admin.ModelAdmin):
    pass

admin.site.register(RaceCourse, RaceCourseAdmin)