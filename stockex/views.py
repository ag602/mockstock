from pprint import pprint
from django.shortcuts import render, redirect, get_object_or_404, HttpResponseRedirect
from django.contrib.auth.models import User

import jwt, StockExchange.settings
from django.views.decorators.csrf import csrf_exempt
from .models import *
from django.http import JsonResponse
from sortedcontainers import SortedList
import datetime
from nsetools import Nse

nse = Nse()


def home(request):
    return render(request, 'exchange.html')


########################################## ORDER BOOK #################################################


# Sample bids and asks lists of type - [quantity, price]. Bids are sorted in decreasing order of price (if
# the price is same of two bids, the older bid gets priority), whereas asks are sorted in increasing order of price(if
# the price is same of two asks, the older ask gets priority)

# Bid: The highest price against which a sell order can be executed
# Ask: The lowest price against which a buy order can be executed
# Spread: The difference between the lowest ask and the highest bid
bids = SortedList([[123, 45.5], [56, 46.76], [24, 46.76]],
                  key=lambda x: -x[1])
asks = SortedList([[123, 45], [24, 46.76]], key=lambda x: +x[1])


########################################## ORDER BOOK END #################################################


def process_market_order(request, offer_id=None):
    offer = get_object_or_404(Offer, id=offer_id)
    print(">Process Market Order View")
    ########## BUY ##########

    # FOR TESTING - INPUT FROM TESTER
    # for i in range(0, 3):
    #     q, p = input("Enter quantity and price: ").split()
    #     asks.add([int(q), float(p)])
    # print(asks)

    # If the offer is buy and the bid offer is greater or equal to the lowest of asks(sell) offers. Then offer is
    # possible to execute. Get current stock price for market orders. NOTE - Here, I have terminated market orders for
    # testing purpose otherwise they are supposed to keep on going until they are completely filled.
    q = nse.get_quote(offer.code)
    last_market_price = q["lastPrice"]
    print(type(last_market_price), offer.price, asks[0][1])
    if offer.direction == 'buy' and last_market_price >= asks[0][1]:
        quantity_filled = 0
        consumed_asks = []
        fill = False
        for k in range(len(asks)):  # Loop through the list of asks(sell)
            ask = asks[k]  # ask[0] is quantity and ask[1] is price
            print("{}th iteration - , asks - {}, Quantity Filled - {}".format(k, asks, quantity_filled))
            if ask[1] > last_market_price:  # Price of ask is too high, stop filling order
                print("Price of ask is too high -", asks, quantity_filled)
                break
            elif quantity_filled == offer.quantity:  # Order was filled
                print("Quantity is filled now. Breaking the loop -", asks, quantity_filled)
                break
            if quantity_filled + ask[0] <= offer.quantity:
                quantity_filled += ask[0]
                trade0 = Trade.objects.create(item_id=offer.item_id, seller_id=offer.item_id, buyer_id=offer.user_id,
                                              quantity=offer.quantity, quantity_fulfilled=ask[0],
                                              price=ask[1], offer_id=offer.id,
                                              created_on=str(datetime.datetime.now().strftime('%H:%M:%S')),
                                              updated_at=str(datetime.datetime.now().strftime('%H:%M:%S')))
                consumed_asks.append(ask)
                fill = True
                print("Completely consume first ask -", quantity_filled, consumed_asks)
            elif quantity_filled + ask[0] > offer.quantity:  # order is filled, ask will be consumed partially
                vol = offer.quantity - quantity_filled
                quantity_filled += vol
                trade1 = Trade.objects.create(item_id=offer.item_id, seller_id=offer.item_id, buyer_id=offer.user_id,
                                              quantity=offer.quantity, quantity_fulfilled=vol,
                                              price=ask[1], offer_id=offer.id,
                                              created_on=str(datetime.datetime.now().strftime('%H:%M:%S')),
                                              updated_at=str(datetime.datetime.now().strftime('%H:%M:%S')))

                ask[0] -= vol
                print("Order will be completely filled now -", asks, quantity_filled)
                fill = True
        # After allocation, if there is still the remains of quantity unfulfilled, add to the order book.
        if quantity_filled < offer.quantity:
            print("Quantity Exceeds. Will be put into OB on price-time basis  -", asks, quantity_filled)
            try:
                bids.insert(bids.bisect_right(last_market_price), [offer.quantity - quantity_filled, last_market_price])
            except Exception as ex:
                print(ex)
        for ask in consumed_asks:
            print("Completely consumed asks will be removed. Asks - {}, Consumed Asks-{}".format(asks, consumed_asks))
            asks.remove(ask)
        if fill:
            return JsonResponse(list(Trade.objects.filter(offer_id=offer.id).values()), status=200, safe=False)
        else:
            print("no")
            return JsonResponse({"error": "Trade was not successful! Order added to Order Book."}, safe=False,
                                status=400)
    ########### SELL ############

    elif offer.direction == 'sell' and last_market_price <= bids[0][1]:
        quantity_filled = 0
        consumed_bids = []
        fill = False
        for k in range(len(bids)):
            bid = bids[k]
            if bid[1] < last_market_price:  # Price of bid is too low, stop filling order
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
                fill = True
            elif quantity_filled + bid[0] > offer.quantity:
                vol = offer.quantity - quantity_filled
                quantity_filled += vol
                trade3 = Trade.objects.create(item_id=offer.item_id, seller_id=offer.user_id, buyer_id=offer.item_id,
                                              quantity=offer.quantity, quantity_fulfilled=vol, price=bid[1],
                                              offer_id=offer.id,
                                              created_on=str(datetime.datetime.now().strftime('%H:%M:%S')),
                                              updated_at=str(datetime.datetime.now().strftime('%H:%M:%S')))
                bid[0] -= vol
                fill = True
        # After allocation, if there is still the remains of quantity unfulfilled, add to the order book.
        if quantity_filled < offer.quantity:
            try:
                bids.insert(bids.bisect_right(last_market_price), [offer.quantity - quantity_filled, last_market_price])
            except Exception as ex:
                print(ex)
        for bid in consumed_bids:
            bids.remove(bid)
            print(asks, bids)

        if fill:
            return JsonResponse(list(Trade.objects.filter(offer_id=offer.id).values()), status=200, safe=False)
        else:
            print("no")
            return JsonResponse({"error": "Trade was not successful! Order added to Order Book."}, safe=False,
                                status=400)

    else:
        # Order did not cross the spread, place in order book
        bids.add([offer.quantity, last_market_price])
        bids.add([offer.quantity, last_market_price])
        return JsonResponse({"error": "Trade was not successful! Order added to Order Book"}, safe=False, status=400)


def process_limit_order(request, offer_id=None):
    offer = get_object_or_404(Offer, id=offer_id)
    print(">Process Limit Order View")
    ########## BUY ##########

    # FOR TESTING - INPUT FROM TESTER
    # for i in range(0, 3):
    #     q, p = input("Enter quantity and price: ").split()
    #     asks.add([int(q), float(p)])
    # print(asks)

    # If the offer is buy and the bid offer is greater or equal to the lowest of asks(sell) offers. Then offer is
    # possible to execute. Get current stock price for limit orders.
    if offer.direction == 'buy' and float(offer.limit_price) >= asks[0][1]:
        quantity_filled = 0
        consumed_asks = []
        fill = False
        for k in range(len(asks)):  # Loop through the list of asks(sell)
            ask = asks[k]  # ask[0] is quantity and ask[1] is price
            print("{}th iteration - , asks - {}, Quantity Filled - {}".format(k, asks, quantity_filled))
            if ask[1] > float(offer.limit_price):  # Price of ask is too high, stop filling order
                print("Price of ask is too high -", asks, quantity_filled)
                break
            elif quantity_filled == offer.quantity:  # Order was filled
                print("Quantity is filled now. Breaking the loop -", asks, quantity_filled)
                break
            if quantity_filled + ask[0] <= offer.quantity:
                quantity_filled += ask[0]
                trade0 = Trade.objects.create(item_id=offer.item_id, seller_id=offer.item_id, buyer_id=offer.user_id,
                                              quantity=offer.quantity, quantity_fulfilled=ask[0],
                                              price=ask[1], offer_id=offer.id,
                                              created_on=str(datetime.datetime.now().strftime('%H:%M:%S')),
                                              updated_at=str(datetime.datetime.now().strftime('%H:%M:%S')))
                consumed_asks.append(ask)
                fill = True
                print("Completely consume first ask -", quantity_filled, consumed_asks)
            elif quantity_filled + ask[0] > offer.quantity:  # order is filled, ask will be consumed partially
                vol = offer.quantity - quantity_filled
                quantity_filled += vol
                trade1 = Trade.objects.create(item_id=offer.item_id, seller_id=offer.item_id, buyer_id=offer.user_id,
                                              quantity=offer.quantity, quantity_fulfilled=vol,
                                              price=ask[1], offer_id=offer.id,
                                              created_on=str(datetime.datetime.now().strftime('%H:%M:%S')),
                                              updated_at=str(datetime.datetime.now().strftime('%H:%M:%S')))

                ask[0] -= vol
                print("Order will be completely filled now -", asks, quantity_filled)
                fill = True
        # After allocation, if there is still the remains of quantity unfulfilled, add to the order book.
        if quantity_filled < offer.quantity:
            print("Quantity Exceeds. Will be put into OB on price-time basis  -", asks, quantity_filled)
            try:
                bids.insert(bids.bisect_right(float(offer.limit_price)),
                            [offer.quantity - quantity_filled, float(offer.limit_price)])
            except Exception as ex:
                print(ex)
        for ask in consumed_asks:
            print("Completely consumed asks will be removed. Asks - {}, Consumed Asks-{}".format(asks, consumed_asks))
            asks.remove(ask)
        if fill:
            return JsonResponse(list(Trade.objects.filter(offer_id=offer.id).values()), status=200, safe=False)
        else:
            print("no")
            return JsonResponse({"error": "Trade was not successful! Order added to Order Book."}, safe=False,
                                status=400)
    ########### SELL ############

    elif offer.direction == 'sell' and float(offer.limit_price) <= bids[0][1]:
        quantity_filled = 0
        consumed_bids = []
        fill = False
        for k in range(len(bids)):
            bid = bids[k]
            if bid[1] < float(offer.limit_price):  # Price of bid is too low, stop filling order
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
                fill = True
            elif quantity_filled + bid[0] > offer.quantity:
                vol = offer.quantity - quantity_filled
                quantity_filled += vol
                trade3 = Trade.objects.create(item_id=offer.item_id, seller_id=offer.user_id, buyer_id=offer.item_id,
                                              quantity=offer.quantity, quantity_fulfilled=vol, price=bid[1],
                                              offer_id=offer.id,
                                              created_on=str(datetime.datetime.now().strftime('%H:%M:%S')),
                                              updated_at=str(datetime.datetime.now().strftime('%H:%M:%S')))
                bid[0] -= vol
                fill = True
        # After allocation, if there is still the remains of quantity unfulfilled, add to the order book.
        if quantity_filled < offer.quantity:
            try:
                bids.insert(bids.bisect_right(float(offer.limit_price)),
                            [offer.quantity - quantity_filled, float(offer.limit_price)])
            except Exception as ex:
                print(ex)
        for bid in consumed_bids:
            bids.remove(bid)
            print(asks, bids)

        if fill:
            return JsonResponse(list(Trade.objects.filter(offer_id=offer.id).values()), status=200, safe=False)
        else:
            print("no")
            return JsonResponse({"error": "Trade was not successful! Order added to Order Book."}, safe=False,
                                status=400)

    else:
        # Order did not cross the spread, place in order book
        bids.add([offer.quantity, float(offer.limit_price)])
        bids.add([offer.quantity, float(offer.limit_price)])
        return JsonResponse({"error": "Trade was not successful! Order added to Order Book"}, safe=False, status=400)


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
    print(">Matching Engine: ", offer)
    if offer.type == 'market':
        print(">Matching Engine: Market Order")
        try:
            return process_market_order(request, offer_id)
        except Exception as ex:
            return JsonResponse({"error - ": ex}, safe=False)

    else:
        print(">Matching Engine: Limit Order")
        return process_limit_order(request, offer_id)


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
        limit_price = request.GET.getlist('limit_price')[0]
        type = request.GET.getlist('type')[0]
        quantity = request.GET.getlist('quantity')[0]
        now = datetime.datetime.now().strftime('%H:%M:%S')
        # c = [f.name for f in Offer._meta.get_fields()]
        instance = Offer.objects.create(user_id=1, item_id=int(id),
                                        code=code, direction=direction, limit_price=limit_price,
                                        type=type, quantity=int(quantity),
                                        companyName=companyName, price=price, is_active=1,
                                        created_on=str(now), updated_at=str(now))
        # Send the offer to matching engine and see what can be done with it. Ideally, the OB should be passed here
        # with the order to be matched.
        print(">Order gateway - ", instance)
        try:
            return matching_engine(request, instance.id)
        except Exception as ex:
            return JsonResponse({"error": ex}, safe=False)
        #     try:
        #         c = matching_engine(request, offer_id=instance.id)
        #         data = list(Trade.objects.filter(offer_id=instance.id).values())
        #         print(">Order gateway(data retrieved after trade) - ", data)
        #         return JsonResponse(data, safe=False)  # Return json response containing the trades of the same offer id
        #     except TypeError:
        #         return JsonResponse({"error": "Trade was not successful! Order is added to Order Book"}, safe=False, status=400)
        # except Exception as ex:
        #     return JsonResponse("Oh! Maybe you forgot GET params? OR The mentioned error may help diagnose issue - {}"
        #                         .format(ex), safe=False)

    return JsonResponse("It worked! Yay!")


from django.core import serializers


def exchanges(request):
    return render(request, 'exchange.html')


def data_gateway(request, symbol=None):
    """
    This endpoint helps to retrieve the latest stock info, which is fulfilled by ajax queries
    from inside the template. For testing and templating, I have used only 1 stock as a reference
    :param code:
    :param request: GET (code)
    :return: JSON Response
    """
    try:
        symbol = request.GET.get('symbol')
        print(symbol)
        # get stock info - for testing
        if not symbol:
            q = nse.get_quote('bhel')
            now = datetime.datetime.now().strftime('%H:%M:%S')  # Time like '23:12:05'
            q["timestamp"] = str(now)
            return JsonResponse({'data': q})
        # get stock info - for production
        else:
            try:
                q = nse.get_quote(symbol)
                now = datetime.datetime.now().strftime('%H:%M:%S')  # Time like '23:12:05'
                q["timestamp"] = str(now)
                return JsonResponse({'data': q})
            except Exception as ex:
                return JsonResponse({"error" : "No stock of this code found" }, status=400, safe=False)
    except Exception as ex:
        return JsonResponse({'data': ex})
