import unittest
from disney_wait_times import DisneyWaitTimesScreen, parse_live

class DisneyWaitTests(unittest.TestCase):
    def test_filters_and_sorts(self):
        payload = {"liveData": [
            {"entityType":"ATTRACTION","status":"OPERATING","name":"B","queue":{"STANDBY":{"waitTime":40}}},
            {"entityType":"ATTRACTION","status":"OPERATING","name":"A","queue":{"STANDBY":{"waitTime":10}}},
            {"entityType":"ATTRACTION","status":"DOWN","name":"C","queue":{"STANDBY":{"waitTime":2}}},
            {"entityType":"ATTRACTION","status":"OPERATING","name":"D","queue":{"PAID_RETURN_TIME":{"waitTime":3}}}
        ]}
        self.assertEqual(parse_live(payload), [("A",10),("B",40)])
        self.assertEqual(parse_live(payload,20), [("A",10)])

    def test_cache_and_offline(self):
        now=[0]
        calls=[]
        def fetch(park):
            calls.append(park)
            if len(calls)>1: raise OSError("offline")
            return {"liveData":[{"entityType":"ATTRACTION","status":"OPERATING","name":"TEST RIDE","queue":{"STANDBY":{"waitTime":20}}}]}
        screen=DisneyWaitTimesScreen(clock=lambda:now[0],fetch=fetch)
        self.assertEqual((screen.render().width,screen.render().height),(64,32))
        self.assertEqual(len(calls),1)
        now[0]=301
        screen.render()
        self.assertEqual(len(calls),2)
        self.assertEqual(screen._rows,[("TEST RIDE",20)])
        self.assertTrue(screen._error)

if __name__=="__main__":
    unittest.main()
