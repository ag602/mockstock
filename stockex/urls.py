from django.urls import path
from django.conf.urls import url
from .views import *

urlpatterns = [
    path('', home, name='home'),
    path('v1/data_gateway/', data_gateway, name='data_gateway'),
    path('v1/order_gateway/', order_gateway, name='order_gateway'),
    path('exchanges/', exchanges, name='exchanges')
]