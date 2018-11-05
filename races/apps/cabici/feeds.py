'''
Created on Apr 20, 2013

@author: steve
'''
from django_ical.views import ICalFeed
from django.contrib.syndication.views import Feed
from races.apps.cabici.models import Race, Club
import datetime
from django.urls import reverse

class EventICALFeed(ICalFeed):
    """
    A simple race calender
    """
    product_id = '-//cabici.net//Races//EN'
    timezone = 'UTC'

    def get_object(self, request, slug=None):
        if slug is None:
            return None
        else:
            return Club.objects.get(slug=slug)

    def items(self, club=None):
        startdate = datetime.date.today()
        if club is None:
            return Race.objects.filter(date__gte=startdate,).order_by('-date')
        else:
            return Race.objects.filter(club=club, date__gte=startdate,).order_by('-date')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return str(item)

    def item_location(self, item):
        return item.location.name

    def item_start_datetime(self, item):
        return datetime.datetime(item.date.year, item.date.month, item.date.day,
                                 item.signontime.hour, item.signontime.minute, item.signontime.second)

    def item_link(self, item):
        return reverse('race', kwargs={'slug': item.club.slug, 'pk': item.id})


from django.utils.feedgenerator import Atom1Feed

class EventAtomFeed(Feed):
    """
    A Race Atom feed
    """
    feed_type = Atom1Feed
    title = "Races on cabici.net"
    link = '/'
    subtitle = 'Races in the next two weeks.'

    def get_object(self, request, slug=None):
        if slug is None:
            return None
        else:
            return Club.objects.get(slug=slug)

    def items(self, club=None):
        startdate = datetime.date.today()
        enddate = startdate + datetime.timedelta(days=14)
        if club is None:
            return Race.objects.filter(date__gte=startdate, date__lt=enddate, status__exact='p').order_by('date')
        else:
            return Race.objects.filter(club=club, date__gte=startdate, date__lt=enddate, status__exact='p').order_by('date')

    def item_title(self, item):
        return "%s - %s, %s" % (item.date.strftime("%b %d"), item.club.slug, item.location)

    def item_description(self, item):

        content = """<p>%s</p>
<p>Location: %s</p>
<pre>%s</pre>""" % (item.title, item.location, item.description)

        return content


    def item_link(self, item):
#        return '/race/'+str(item.id)
        return reverse('race', kwargs={'slug': item.club.slug, 'pk': item.id})
