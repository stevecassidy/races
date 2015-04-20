import unittest
import vcr


from races.ingest.lacc import *

class LACCTests(unittest.TestCase):
    
    @vcr.use_cassette('fixtures/vcr_cassettes/lacc.yaml')
    def test_lacc(self):
        
        races = ingest()
        
        self.assertEqual(33, len(races))
        
        self.assertEqual("Seniors Track Training", races[0]['title'])
        
        
        
        
if __name__ == '__main__':
    unittest.main()