from pprint import pprint
from django.shortcuts import render, redirect, get_object_or_404, HttpResponseRedirect
from django.contrib.auth.models import User
from .serializers import CreateUserSerializer
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import jwt, StockExchange.settings
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from .models import *
from django.http import JsonResponse
from rest_framework.decorators import parser_classes
from rest_framework.parsers import JSONParser
import yfinance as yf

import datetime
from nsetools import Nse

nse = Nse()
# Create your views here.

from rest_framework.exceptions import ValidationError


def home(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('login')
    else:
        return render(request, 'exchange.html')


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    serializer = CreateUserSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
    user = serializer.save()
    refresh = RefreshToken.for_user(user)
    tokens = {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }
    return Response(tokens, status.HTTP_201_CREATED)


@csrf_exempt
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = User.objects.get(username=username)
        if user:
            try:
                # payload = jwt_payload_handler(user)
                payload = {"user_id": user.id}
                token = jwt.encode(payload, StockExchange.settings.SECRET_KEY)
                user_details = {}
                user_details['name'] = "%s %s" % (
                    user.first_name, user.last_name)
                user_details['token'] = token
                # user_logged_in.send(sender=user.__class__,
                #                     request=request, user=user)
                user = authenticate(request, username=username, password=password)
                return HttpResponseRedirect('/exchanges')

            except Exception as e:
                raise e
        else:
            res = {
                'error': 'can not authenticate with the given credentials or the account has been deactivated'}
            return Response(res, status=status.HTTP_403_FORBIDDEN)
    else:
        return render(request, 'login.html')


# sample_order_book = {"bp1":45.06, "bq1":100000, "bp2":45.00, "bq2":100000, "bp3":44.00, "bq3":100000,
#                      "bp4":46.00, "bq4":100000, "bp5":45.50, "bq5":100000,"sp1":45.10, "sq1":100000,
#                      "sp2":45.30, "sq2":100000, "sp3":46.00, "sq3":100000, "sp4":45.45, "sq4":100000,
#                     "sp5":44.95, "sq5":100000}

from sortedcontainers import SortedList


    ########################################## ORDER BOOK #################################################


# Sample bids and asks lists of type - [quantity, price]. Bids are sorted in decreasing order of price (if
# the price is same of two bids, the older bid gets priority), whereas asks are sorted in increasing order of price(if
# the price is same of two asks, the older ask gets priority)

# Bid: The highest price against which a sell order can be executed
# Ask: The lowest price against which a buy order can be executed
# Spread: The difference between the lowest ask and the highest bid
bids = SortedList([[123, 45.5], [56, 46.76],[24, 46.76]],
                  key=lambda x: -x[1])
asks = SortedList([[123, 45.5], [24, 46.76]], key=lambda x: +x[1])

    ########################################## ORDER BOOK END #################################################


def process_market_order(request, offer_id=None):
    offer = get_object_or_404(Offer, id=offer_id)

    ########## BUY ##########

    # If the offer is buy and the bid offer is greater or equal to the lowest of asks(sell) offers. Then offer is
    # possible to execute. Get current stock price for market orders. NOTE - Here, I have terminated market orders for
    # testing purpose otherwise they are supposed to keep on going until they are completely filled.
    q = nse.get_quote(offer.code)
    print("START1 -", asks)
    if offer.direction == 'buy' and q['lastPrice'] >= asks[0][1]:
        quantity_filled = 0
        consumed_asks = []
        for k in range(len(asks)):  # Loop through the list of asks(sell)
            ask = asks[k]  # ask[0] is quantity and ask[1] is price
            print("START2 -", asks, quantity_filled)
            if ask[1] > q['lastPrice']:  # Price of ask is too high, stop filling order
                print("START3 -", asks, quantity_filled)
                break
            elif quantity_filled == offer.quantity:  # Order was filled
                print("START4 -", asks, quantity_filled)
                break
            if quantity_filled + ask[0] <= offer.quantity:
                print("START5 -", asks, quantity_filled)
                quantity_filled += ask[0]
                trade0 = Trade.objects.create(item_id=offer.item_id, seller_id=offer.item_id, buyer_id=offer.user_id,
                                              quantity=offer.quantity, quantity_fulfilled=ask[0],
                                              price=ask[1], offer_id=offer.id,
                                              created_on=str(datetime.datetime.now().strftime('%H:%M:%S')),
                                              updated_at=str(datetime.datetime.now().strftime('%H:%M:%S')))
                consumed_asks.append(ask)
                print("START6 -", asks, quantity_filled)
            elif quantity_filled + ask[0] > offer.quantity:  # order is filled, ask will be consumed partially
                vol = offer.quantity - quantity_filled
                quantity_filled += vol
                trade1 = Trade.objects.create(item_id=offer.item_id, seller_id=offer.item_id, buyer_id=offer.user_id,
                                              quantity=offer.quantity, quantity_fulfilled=vol,
                                              price=ask[1], offer_id=offer.id,
                                              created_on=str(datetime.datetime.now().strftime('%H:%M:%S')),
                                              updated_at=str(datetime.datetime.now().strftime('%H:%M:%S')))

                ask[0] -= vol
                print("START7 -", asks, quantity_filled)
        # After allocation, if there is still the remains of quantity unfulfilled, add to the order book.
        if quantity_filled < offer.quantity:
            print("START8 -", asks, quantity_filled)
            bids.insert(bids.bisect_right(q['lastPrice']), [offer.quantity - quantity_filled, q['lastPrice']])
        for ask in consumed_asks:
            print("START9 -", asks, quantity_filled)
            asks.remove(ask)

    ########### SELL ############

    elif offer.direction == 'sell' and q['lastPrice'] <= bids[0][1]:
        quantity_filled = 0
        consumed_bids = []
        for k in range(len(bids)):
            bid = bids[k]
            if bid[1] < q['lastPrice']:  # Price of bid is too low, stop filling order
                break
            if quantity_filled == offer.quantity:  # Order was filled
                break

            if quantity_filled + bid[0] <= offer.quantity:  # order not yet filled, bid will be consumed whole
                quantity_filled += bid[0]
                trade2 = Trade.objects.create(item_id=offer.item_id, seller_id=offer.user_id, buyer_id=offer.item_id,
                                              quantity=offer.quantity, quantity_fulfilled=bid[0], price=bid[1],
                                              offer_id=offer.id,
                                              created_on=str(datetime.datetime.now().strftime('%H:%M:%S')),
                                              updated_at=str(datetime.datetime.now().strftime('%H:%M:%S')))
                consumed_bids.append(bid)
            elif quantity_filled + bid[0] > offer.quantity:
                vol = offer.quantity - quantity_filled
                quantity_filled += vol
                trade3 = Trade.objects.create(item_id=offer.item_id, seller_id=offer.user_id, buyer_id=offer.item_id,
                                              quantity=offer.quantity, quantity_fulfilled=vol, price=bid[1],
                                              offer_id=offer.id,
                                              created_on=str(datetime.datetime.now().strftime('%H:%M:%S')),
                                              updated_at=str(datetime.datetime.now().strftime('%H:%M:%S')))
                bid[0] -= vol
        # After allocation, if there is still the remains of quantity unfulfilled, add to the order book.
        if quantity_filled < offer.quantity:
            bids.insert(bids.bisect_right(q['lastPrice']), [offer.quantity - quantity_filled, q['lastPrice']])
        for bid in consumed_bids:
            bids.remove(bid)
            print(asks, bids)

    else:
        # Order did not cross the spread, place in order book
        bids.add([offer.quantity, offer.price])
        bids.add([offer.quantity, offer.price])
        return JsonResponse("Failed! Order given neither buy or sell.", safe=False)


print("START10 -", asks)


def process_limit_order(request, offer_id=None):
    offer = get_object_or_404(Offer, id=offer_id)
    ########## BUY ##########

    # If the offer is buy and the bid offer is greater or equal to the lowest of asks(sell) offers. Then offer is
    # possible to execute.
    if offer.direction == 'buy' and offer.limit_price >= asks[0][1]:
        quantity_filled = 0
        consumed_asks = []
        for k in range(len(asks)):  # Loop through the list of asks(sell)
            ask = asks[k]  # ask[0] is quantity and ask[1] is price
            if ask[1] > offer.limit_price:  # Price of ask is too high, stop filling order
                break
            elif quantity_filled == offer.quantity:  # Order was filled
                break
            if quantity_filled + ask[0] <= offer.quantity:
                quantity_filled += ask[0]
                trade0 = Trade.objects.create(item_id=offer.item_id, seller_id=offer.item_id, buyer_id=offer.user_id,
                                              quantity=offer.quantity, quantity_fulfilled=ask[0],
                                              price=ask[1], offer_id=offer.id,
                                              created_on=str(datetime.datetime.now().strftime('%H:%M:%S')),
                                              updated_at=str(datetime.datetime.now().strftime('%H:%M:%S')))
                consumed_asks.append(ask)
            elif quantity_filled + ask[0] > offer.quantity:  # order is filled, ask will be consumed partially
                vol = offer.quantity - quantity_filled
                quantity_filled += vol
                trade1 = Trade.objects.create(item_id=offer.item_id, seller_id=offer.item_id, buyer_id=offer.user_id,
                                              quantity=offer.quantity, quantity_fulfilled=vol,
                                              price=ask[1], offer_id=offer.id,
                                              created_on=str(datetime.datetime.now().strftime('%H:%M:%S')),
                                              updated_at=str(datetime.datetime.now().strftime('%H:%M:%S')))

                ask[0] -= vol
        # After allocation, if there is still the remains of quantity unfulfilled, add to the order book.
        if quantity_filled < offer.quantity:
            bids.insert(bids.bisect_right(offer.limit_price), [offer.quantity - quantity_filled, offer.limit_price])
        for ask in consumed_asks:
            asks.remove(ask)

    ########## SELL ##########

    elif offer.direction == 'sell' and offer.limit_price <= bids[0][1]:
        quantity_filled = 0
        consumed_bids = []
        for k in range(len(bids)):
            bid = bids[k]
            if bid[1] < offer.limit_price:  # Price of bid is too low, stop filling order
                break
            if quantity_filled == offer.quantity:  # Order was filled
                break

            if quantity_filled + bid[0] <= offer.quantity:  # order not yet filled, bid will be consumed whole
                quantity_filled += bid[0]
                trade2 = Trade.objects.create(item_id=offer.item_id, seller_id=offer.user_id, buyer_id=offer.item_id,
                                              quantity=offer.quantity, quantity_fulfilled=bid[0], price=bid[1],
                                              offer_id=offer.id,
                                              created_on=str(datetime.datetime.now().strftime('%H:%M:%S')),
                                              updated_at=str(datetime.datetime.now().strftime('%H:%M:%S')))
                consumed_bids.append(bid)
            elif quantity_filled + bid[0] > offer.quantity:
                vol = offer.quantity - quantity_filled
                quantity_filled += vol
                trade3 = Trade.objects.create(item_id=offer.item_id, seller_id=offer.user_id, buyer_id=offer.item_id,
                                              quantity=offer.quantity, quantity_fulfilled=vol, price=bid[1],
                                              offer_id=offer.id,
                                              created_on=str(datetime.datetime.now().strftime('%H:%M:%S')),
                                              updated_at=str(datetime.datetime.now().strftime('%H:%M:%S')))
                bid[0] -= vol
        # After allocation, if there is still the remains of quantity unfulfilled, add to the order book.
        if quantity_filled < offer.quantity:
            bids.insert(bids.bisect_right(offer.limit_price), [offer.quantity - quantity_filled, offer.limit_price])
        for bid in consumed_bids:
            bids.remove(bid)

    else:
        # Order did not cross the spread, place in order book
        bids.add([offer.quantity, offer.price])
        bids.add([offer.quantity, offer.price])
        return JsonResponse("Failed! Order given neither buy or sell.", safe=False)


def matching_engine(request, offer_id=None):
    """
    All incoming orders are passed on to this engine, which then tries to match them against
    the passive orders in the Order Book (OB). The book contains all limit orders for which no matches have been
    found as of yet, divided in a bid direction (sorted in ascending order) and an ask direction (sorted in descending
    order). If no matches can be found for a new order it will also be stored in the OB, on the appropriate side.
    :param request: GET - offer_id
    :return: None
    """
    offer = get_object_or_404(Offer, id=offer_id)
    if offer.type == 'market':
        c = process_market_order(request, offer_id)
    else:
        c = process_limit_order(request, offer_id)
    return JsonResponse(c, safe=False)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def order_gateway(request):
    """
    Orders/Offers represent the core piece of the exchange. Every bid/ask is an Order/Offer.
    This endpoint receives order from the investor/seller, saves the order in the database and
    sends the order to the matching engine for trade.
    :param request: GET - price, companyName, timestamp, code, id, limit_price, type, quantity
    :return: JSON Response
    """
    if request.method == 'GET':
        code = request.GET.getlist('code')[0]
        q = nse.get_quote(code)
        price = q['lastPrice']
        companyName = q['companyName']
        id = request.GET.getlist('id')[0]
        direction = request.GET.getlist('direction')[0]
        print(direction)
        limit_price = request.GET.getlist('limit_price')[0]
        type = request.GET.getlist('type')[0]
        quantity = request.GET.getlist('quantity')[0]
        now = datetime.datetime.now().strftime('%H:%M:%S')
        # c = [f.name for f in Offer._meta.get_fields()]
        try:
            instance = Offer.objects.create(user_id=1, item_id=int(id),
                                            code=code, direction=direction, limit_price=limit_price,
                                            type=type, quantity=int(quantity),
                                            companyName=companyName, price=price, is_active=1,
                                            created_on=str(now), updated_at=str(now))
            # Send the offer to matching engine and see what can be done with it.
            try:
                matching_engine(request, offer_id=instance.id)
                data = list(Trade.objects.filter(offer_id=instance.id).values())
                return JsonResponse(data, safe=False)  # Return json response containing the trades of the same offer id
            except TypeError:
                return JsonResponse(list(Trade.objects.filter(offer_id=instance.id).values()), safe=False)
        except Exception as ex:
            return JsonResponse("Oh! Maybe you forgot GET params? OR The mentioned error may help diagnose issue - {}"
                                .format(ex), safe=False)

    return JsonResponse("It worked! Yay!", safe=False)


from django.core import serializers


@api_view(['GET'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def exchanges(request):
    return render(request, 'exchange.html')


@api_view(['GET', 'POST'])
@parser_classes([JSONParser])
@renderer_classes((TemplateHTMLRenderer, JSONRenderer))
@permission_classes([permissions.AllowAny])
def data_gateway(request):
    """
    This endpoint helps to retrieve the latest stock info, which is fulfilled by ajax queries
    from inside the template.
    :param request: GET or POST
    :return: JSON Response
    """
    try:
        symbol = request.GET.get('symbol')
        # get stock info - for testing
        if not symbol:
            q = nse.get_quote('bhel')
            now = datetime.datetime.now().strftime('%H:%M:%S')  # Time like '23:12:05'
            q["timestamp"] = str(now)
            return JsonResponse({'data': q})
        # get stock info - for production
        else:
            q = nse.get_quote(symbol)
            now = datetime.datetime.now().strftime('%H:%M:%S')  # Time like '23:12:05'
            q["timestamp"] = str(now)
            return JsonResponse({'data': q})
    except Exception as ex:
        return JsonResponse({'data': ex})
