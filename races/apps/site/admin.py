'''
Created on Apr 15, 2013

@author: steve
'''
from django.contrib import admin
from django import forms
from races.apps.site.models import Club, RaceCourse, Race, STATUS_CHOICES
from races.apps.site.usermodel import PointScore

admin.site.register(Club)


class RaceAdmin(admin.ModelAdmin):

    model = Race
    date_hierarchy = 'date'
    list_display = ['date', 'club', 'title', 'location', 'status']
    list_filter = ['club', 'location', 'status']
    list_editable = ['status', 'location']
    actions = ['make_published', 'make_draft', 'make_withdrawn']
    save_as = True

    def make_published(self, request, queryset):
        self.set_status(request, queryset, 'p')

    def make_draft(self, request, queryset):
        self.set_status(request, queryset, 'd')

    def make_withdrawn(self, request, queryset):
        self.set_status(request, queryset, 'w')

    def set_status(self, request, queryset, status):
        rows_updated = queryset.update(status=status)
        if rows_updated == 1:
            message_bit = "1 race was"
        else:
            message_bit = "%s races were" % rows_updated
        self.message_user(request, "%s successfully marked as %s." % (message_bit, status))


    class Meta:
        pass

admin.site.register(Race, RaceAdmin)

class PointScoreAdmin(admin.ModelAdmin):
    pass

admin.site.register(PointScore, PointScoreAdmin)


class RaceCourseAdmin(admin.ModelAdmin):
    pass

admin.site.register(RaceCourse, RaceCourseAdmin)

from races.apps.site.usermodel import Rider, RaceResult, ClubGrade
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

class ClubGradeAdmin(admin.ModelAdmin):
    pass

admin.site.register(ClubGrade, ClubGradeAdmin)

class RiderInline(admin.StackedInline):
    model = Rider
    can_delete = False

# Define a new User admin
class UserAdmin(UserAdmin):
    inlines = (RiderInline, )

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


class RaceResultAdmin(admin.ModelAdmin):
    pass

admin.site.register(RaceResult, RaceResultAdmin)
