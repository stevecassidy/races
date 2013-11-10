'''
Created on Apr 20, 2013

@author: steve
'''
from django_ical.views import ICalFeed
from django.contrib.syndication.views import Feed
from races.apps.site.models import Race
import datetime
from django.core.urlresolvers import reverse

class EventICALFeed(ICalFeed):
    """
    A simple race calender
    """
    product_id = '-//cabici.net//Races//EN'
    timezone = 'UTC'

    def items(self):
        return Race.objects.all().order_by('-date')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return str(item)

    def item_location(self, item):
        return item.location.name

    def item_start_datetime(self, item):
        return datetime.datetime(item.date.year, item.date.month, item.date.day,
                                 item.time.hour, item.time.minute, item.time.second)

    def item_link(self, item):
        return '/race/'+str(item.id)
#        return reverse('race', kwargs={'site:pk': item.id})



class EventRSSFeed(Feed):
    """
    A Race RSS feed
    """
    title = "Upcoming Races on cabici.net"
    link = '/rss'
    description = 'Upcoming races from cabici.net'

    def items(self):
        startdate = datetime.date.today()
        enddate = startdate + datetime.timedelta(days=14)
        return Race.objects.filter(date__gte=startdate, date__lt=enddate, status__exact='p').order_by('-date')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return str(item)


    def item_link(self, item):
#        return '/race/'+str(item.id)
        return reverse('site:race', kwargs={'slug': item.club.slug, 'pk': item.id})
