
import ngram
from races.apps.site.models import RaceCourse


def find_location(name):
    """Find a RaceCourse using an approximate match to
    the given name, return the best matching RaceCourse instance"""
    
    courses = RaceCourse.objects.all()
    
    ng = ngram.NGram(courses, key=str)
    
    return ng.finditem(name)


