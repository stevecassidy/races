
import ngram
from races.apps.site.models import RaceCourse, Race, Club


def find_location(name):
    """Find a RaceCourse using an approximate match to
    the given name, return the best matching RaceCourse instance"""
    
    courses = RaceCourse.objects.all()
    
    ng = ngram.NGram(courses, key=str)
    
    location = ng.finditem(name)

    if location == None:
        location = RaceCourse.objects.get(name="Unknown")
        
    return location



def ingest_club(races, club=None):
    
    for r in races:

        try:
            location = find_location(r['location'])
            if club == None:
                thisclub = Club.objects.get(slug=r['club'])
            else:
                thisclub = club
            
            if len(r['title']) > 100:
                r['title'] = r['title'][:99]
            
            race = Race(title=r['title'], date=r['date'], time=r['time'], club=thisclub, location=location, url=r['url'])
            race.save()
        except Exception as e:
            print "Error: ", e