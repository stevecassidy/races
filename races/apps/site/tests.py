from django.test import TestCase
from django.core.urlresolvers import reverse

from races.apps.site.models import Club, RaceCourse, Race
from datetime import datetime, timedelta

class RacesTests(TestCase):
    
    fixtures = ['clubs', 'courses']
    
    def setUp(self):
        
        today = datetime.today()
        yesterday = today - timedelta(1)
        tomorrow = today + timedelta(1)
        nextweek = today + timedelta(7)
        nextfortnight = today + timedelta(14)
        nextthreeweeks = today + timedelta(21)
        
        self.wmcc = Club.objects.get(slug='WMCC')
        self.lacc = Club.objects.get(slug='LACC')
        
        lansdowne = RaceCourse.objects.get(name='Lansdowne Park')
        sop = RaceCourse.objects.get(name='Tennis Centre, SOP')
        
        r1 = Race(title='Yesterday 1 W', date=yesterday, club=self.wmcc, time="7:00", url=self.wmcc.url, location=lansdowne)
        r2 = Race(title='Today 2 W', date=today, club=self.wmcc, time="7:00", url=self.wmcc.url, location=lansdowne)
        r3 = Race(title='Tomorrow 3 W', date=tomorrow, club=self.wmcc, time="7:00", url=self.wmcc.url, location=lansdowne)
        r4 = Race(title='Next Week 4 W', date=nextweek, club=self.wmcc, time="7:00", url=self.wmcc.url, location=lansdowne)
        r5 = Race(title='Fortnight 5 W', date=nextfortnight, club=self.wmcc, time="7:00", url=self.wmcc.url, location=lansdowne)
        r6 = Race(title='Three Weeks 6 W', date=nextthreeweeks, club=self.wmcc, time="7:00", url=self.wmcc.url, location=lansdowne)
        
        r1.save()
        r2.save()
        r3.save()
        r4.save()
        r5.save()
        r6.save()
        
        r7 = Race(title='Yesterday 1 L', date=yesterday, club=self.lacc, time="8:00", url=self.lacc.url, location=sop)
        r8 = Race(title='Today 2 L', date=today, club=self.lacc, time="8:00", url=self.lacc.url, location=sop)
        r9 = Race(title='Tomorrow 3 L', date=tomorrow, club=self.lacc, time="8:00", url=self.lacc.url, location=sop)
        r10 = Race(title='Next Week 4 L', date=nextweek, club=self.lacc, time="8:00", url=self.lacc.url, location=sop)  
        r11 = Race(title='Fortnight 5 L', date=nextfortnight, club=self.lacc, time="8:00", url=self.lacc.url, location=sop)  
        r12 = Race(title='Three Weeks 6 L', date=nextthreeweeks, club=self.lacc, time="8:00", url=self.lacc.url, location=sop)    
        
        r7.save()
        r8.save()
        r9.save()
        r10.save()
        r11.save()
        r12.save()
        
    def test_home_page(self):

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "About cabici", 1, 200)
    
    def test_home_page_race_list(self):
        """Test that the home page lists the next two
        weeks of races, starting from today"""
        
        
        response = self.client.get(reverse('site:home'))
        self.assertNotContains(response, "Yesterday 1 W")
        self.assertContains(response, "Today 2 W")
        self.assertContains(response, "Tomorrow 3 W")
        self.assertContains(response, "Next Week 4 W")
        self.assertNotContains(response, "Fortnight 5 W")
        self.assertNotContains(response, "Three Weeks 6 W")
        
        
    def test_race_list_page(self):
        """Test that the race list page has all future
        races including today"""
        
        response = self.client.get(reverse('site:races'))
        
        self.assertNotContains(response, "Yesterday 1 W")
        self.assertContains(response, "Today 2 W")
        self.assertContains(response, "Today 2 L")
        self.assertContains(response, "Tomorrow 3 W")
        self.assertContains(response, "Next Week 4 W")
        self.assertContains(response, "Fortnight 5 W")
        self.assertContains(response, "Three Weeks 6 W")
        self.assertContains(response, "Three Weeks 6 L")
        
        
    def test_club_page(self):
        """Test that the club page has all future
        races for the club including today"""
        
        response = self.client.get(reverse('site:club', kwargs={'pk': self.wmcc.id}))
        
        self.assertNotContains(response, "Yesterday 1 W")
        self.assertContains(response, "Today 2 W")
        self.assertContains(response, "Tomorrow 3 W")
        self.assertContains(response, "Next Week 4 W")
        self.assertContains(response, "Fortnight 5 W")
        self.assertContains(response, "Three Weeks 6 W")    
        self.assertNotContains(response, "Today 2 L")
        
        
        
        