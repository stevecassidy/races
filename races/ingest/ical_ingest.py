
from icalendar import Calendar, Event
from urllib2 import urlopen
import datetime

def ingest_ical(calendar_url):
    """Import races from an icalendar feed"""
    
    print calendar_url
    h = urlopen(calendar_url)
    ical_text = h.read()
    h.close()
    
    cal = Calendar.from_ical(ical_text)
    today = datetime.datetime.today()
    
    for component in cal.walk():
        
        if component.has_key('DTSTART'):
            start = component.decoded('DTSTART')
            title = component.decoded('SUMMARY', '')
            title = component.decoded('DESCRIPTION', '')
            
            if start.year >= today.year and start.month >= today.month:
                print "FUTURE: ", start, title
            else:
                print "PAST: ", start, title
        else:
            print component.name
        
        
        

if __name__=='__main__':
    
    url = 'http://northernsydneycyclingclub.org.au/calendar/ical/2013-05'
    url = 'https://www.google.com/calendar/ical/account%40manlywarringahcc.org.au/public/basic.ics'
    url = 'http://www.centralcoastcyclingclub.com.au/calendar/ical/2013-07'
    
    races = ingest_ical(url)