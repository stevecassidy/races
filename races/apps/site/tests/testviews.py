from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect

from races.apps.site.models import Club, RaceCourse, Race
from datetime import datetime, timedelta



class ViewTests(TestCase):
    
    fixtures = ['clubs', 'courses']
    
    def setUp(self):
        
        User.objects.create_user('test', password='test')
        
        today = datetime.today()
        yesterday = today - timedelta(1)
        tomorrow = today + timedelta(1)
        nextweek = today + timedelta(7)
        nextfortnight = today + timedelta(14)
        nextthreeweeks = today + timedelta(21)
        
        
        self.wmcc = Club.objects.get(slug='Waratahs')
        self.lacc = Club.objects.get(slug='LACC')
        
        self.lansdowne = RaceCourse.objects.get(name='Lansdowne Park')
        self.sop = RaceCourse.objects.get(name='Tennis Centre, SOP')
        
        r = []
        r.append(Race(title='Yesterday 1 W', date=yesterday, club=self.wmcc, time="7:00", status='p', url=self.wmcc.url, location=self.lansdowne))
        r.append(Race(title='Today 2 W', date=today, club=self.wmcc, time="7:00", status='p', url=self.wmcc.url, location=self.lansdowne))
        r.append(Race(title='Tomorrow 3 W', date=tomorrow, club=self.wmcc, time="7:00", status='p', url=self.wmcc.url, location=self.lansdowne))
        r.append(Race(title='Next Week 4 W', date=nextweek, club=self.wmcc, time="7:00", status='p', url=self.wmcc.url, location=self.lansdowne))
        r.append(Race(title='Fortnight 5 W', date=nextfortnight, club=self.wmcc, time="7:00", status='p', url=self.wmcc.url, location=self.lansdowne))
        r.append(Race(title='Three Weeks 6 W', date=nextthreeweeks, club=self.wmcc, time="7:00", status='p', url=self.wmcc.url, location=self.lansdowne))
        r.append(Race(title='Not Published', date=tomorrow, club=self.wmcc, time="7:00", status='d', url=self.wmcc.url, location=self.lansdowne))
          

        r.append(Race(title='Yesterday 1 L', date=yesterday, club=self.lacc, time="8:00", status='p', url=self.lacc.url, location=self.sop))
        r.append(Race(title='Today 2 L', date=today, club=self.lacc, time="8:00", status='p', url=self.lacc.url, location=self.sop))
        r.append(Race(title='Tomorrow 3 L', date=tomorrow, club=self.lacc, time="8:00", status='p', url=self.lacc.url, location=self.sop))
        r.append(Race(title='Next Week 4 L', date=nextweek, club=self.lacc, time="8:00", status='p', url=self.lacc.url, location=self.sop))  
        r.append(Race(title='Fortnight 5 L', date=nextfortnight, club=self.lacc, time="8:00", status='p', url=self.lacc.url, location=self.sop))  
        r.append(Race(title='Three Weeks 6 L', date=nextthreeweeks, club=self.lacc, time="8:00", status='p',  url=self.lacc.url, location=self.sop))    
        

        for race in r:
            race.save()
        
    def test_home_page(self):
        """The home page returns a 200 response"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        #self.assertContains(response, "About cabici", 1, 200)
    
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
    
        # draft races shouldn't appear
        self.assertNotContains(response, "Not Published")
        
        
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
        
        
    def test_race_list_page_month(self):
        """Test that the race list page for a given month works"""
        
        today = datetime.today() 
        url = today.strftime('/races/%Y/%m/')
        response = self.client.get(url)
        
        # just check for today - should check more TODO
        self.assertContains(response, "Today 2 W")
        self.assertContains(response, "Today 2 L")
        
                
    def test_club_page(self):
        """Test that the club page has all future
        races for the club including today"""
        
        response = self.client.get(reverse('site:club', kwargs={'slug': self.wmcc.slug}))
        
        self.assertNotContains(response, "Yesterday 1 W")
        self.assertContains(response, "Today 2 W")
        self.assertContains(response, "Tomorrow 3 W")
        self.assertContains(response, "Next Week 4 W")
        self.assertContains(response, "Fortnight 5 W")
        self.assertContains(response, "Three Weeks 6 W")    
        self.assertNotContains(response, "Today 2 L")
        
        
    def test_create_race(self):
        """Test the creation of a new race"""
        
        # count races for wmcc
        n = self.wmcc.race_set.count()
        
        # need to login first
        
        response = self.client.login(username='test', password='test')
        self.assertTrue(response, "Login failed in test, aborting")
        
        url = reverse('site:race_create')
        # first get
        response = self.client.get(url)
        
        self.assertContains(response, "form")
        self.assertContains(response, 'name="club"')
        self.assertContains(response, "Create New Race")
        
        data = {'club': self.wmcc.id, 
                'location': self.lansdowne.id,
                'title': 'Test Race',
                'date': '2014-12-13',
                'time': '08:00',
                'status': 'd',
                'url': 'http://example.org/'}
        
        response = self.client.post(url, data)
        # expect a redirect response to the race page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(isinstance(response, HttpResponseRedirect))  
        self.assertIn( 'Waratahs', response.get('Location'))
        
        # should have one more race
        
        self.assertEqual(n+1, self.wmcc.race_set.count())
        
        
    def test_create_race_series(self):
        """Test the creation of many new races"""
    
        # count races for wmcc
        n = self.wmcc.race_set.count()
    
        # need to login first
    
        response = self.client.login(username='test', password='test')
        self.assertTrue(response, "Login failed in test, aborting")
    
        url = reverse('site:race_create')
        # first get
        response = self.client.get(url)
    
        self.assertContains(response, "form")
        self.assertContains(response, 'name="club"')
        self.assertContains(response, "Create New Race")
    
        data = {'club': self.wmcc.id, 
                'location': self.lansdowne.id,
                'title': 'Test Race',
                'date': '2014-12-13',
                'time': '08:00',
                'status': 'd',
                'weekly': 'y',
                'number': 6,
                'url': 'http://example.org/'}
    
        response = self.client.post(url, data)
        # expect a redirect response to the race page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(isinstance(response, HttpResponseRedirect))  
        self.assertIn( 'Waratahs', response.get('Location'))
    
        # should have six more races    
        self.assertEqual(n+6, self.wmcc.race_set.count())
    
    