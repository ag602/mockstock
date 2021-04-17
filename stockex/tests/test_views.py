from django.test import TestCase, Client
from stockex.views import *
from django.urls import reverse
from stockex.models import *
import json
from sortedcontainers import SortedList


#########################  LEFT INCOMPLETE DUE TO TIME CONSTRAINTS  #########################


class YourTestClass(TestCase):
    # @classmethod
    # def setUpTestData(cls):
    #     pass
    #
    # def setUp(self):
    #     print("setUp: Run once for every test method to setup clean data.")
    #     pass

    def test_order_gateway(self):
        data = {
            "code": "bhel",
            "id": 1,
            "direction": "buy",
            "limit_price": 0,
            "type": "market",
            "quantity": 123,
        }
        self.response = self.client.get("/v1/order_gateway/", data=data)
        print(self.response.content)
        # self.assertEqual(self.response.status_code, status.HTTP_201_CREATED)
        self.assertJSONEqual(
            str(self.response.content, encoding='utf8'),
            {'status': 'success'}
        )
        self.assertEqual(Offer.objects.count(), 1)
