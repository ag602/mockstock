
**Mock Stock Exchange App**  
----  

**INTRODUCTION**

An order matching engine operates on an Order Book (OB) to match buyers(bids) and sellers(asks), resulting in a series of trades. The most common matching algorithm is the Price-Time priority Algorithm. Orders in OB are filled primarily based on price; if multiple orders are present at the same price, then the oldest(first-placed) order will be filled first. This works on the principle of FIFO queue: first in, first out.  

**SETUP**
 
 1. Clone the repo
 2. Activate virtual env: `python -m venv env`
 3. Install requirements: `pip install -r requirements.txt`
 4. Play!

**LIBRARIES/FRAMEWORKS USED**
 
 1. django - [Link](https://www.djangoproject.com/)
 2. djangorestframework - [Link](https://www.django-rest-framework.org/)
 3. djangorestframework-simplejwt - [Link](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/)
 4. nsetools - [Link](https://nsetools.readthedocs.io/)
 5. pymongo - [Link](https://pymongo.readthedocs.io/en/stable/)
 6. djongo - [Link](https://www.djongomapper.com/)
 7. sortedcontainers - [Link](http://www.grantjenks.com/docs/sortedcontainers/)
 
## API Paths  
* [**/v1/data_gateway/**](#v1datagateway)  
  
  
* [**/v1/order_gateway/**](#v1ordergateway)  
  
  
  
___  
### /v1/data_gateway/  
**Allowed Methods** : `GET` | `POST`  
<br>**URL Params** : **Optional:** `symbol=[string]`  
<br>**Access Level** : AUTHORIZED  
<br>**Additional**:Return a json object of all/particular trade data  
  
### /v1/order_gateway/  
**Allowed Methods** : `GET`  
<br>**URL Params** : **Required:** `id=[int], code=[int], direction=[string], limit_price=[string], type = [string], quantity=[int]`  
<br>**Access Level** : AUTHORIZED  
<br>**Additional**: Return a confirmation if trade is successful, otherwise throw an error. <em> limit_price </em> should be 0 if type is "market" . If type is "limit", set the limit_price accordingly. <em>direction</em> is either "buy" or "sell". <em>quantity</em> is the number of stocks you want to buy if your current order is a limit order  
 
 ## HOW DOES IT WORK? 

 
****NON-TECHNICAL EXPLANATION****</br>
An order is simply an offer (buy/sell) against a security which is not executed yet. An investor places an order which is executed by the matching engine using various algorithms (the best one being *Price-Time*). The execution of order is based on several (a lot) of factors such as - Markey/Limit order, limit price if the order is a limit order, available  quantity, an IOC/Day order, etc. Here, I have implemented a simple price time priority algorithm for both Market/Limit orders. The order will be partially filled, if the OB has no more units left to fill your desired amount. If an OB entry is consumed fully, it will be removed from the list. If some part of your order is unfulfilled, it will be recorded in the OB on a price-time basis. 

----

****TECHNICAL EXPLANATION****</br>
There are 2 endpoints - `/v1/order_gateway` and `/v1/data_gateway`. 

**Example Request-** 

 1.  `http://127.0.0.1:8000/v1/order_gateway/?type=market&quantity=15&limit_price=0&code=bhel&id=1&direction=sell`
 
**Success Response** 
**Code-** 200
**Content-** This endpoint returns a json object of the trade (if fulfilled) - 
```json
  [
    {
    "id": 28,
    "item_id": 1,
    "seller_id": 1,
    "buyer_id": 1,
    "quantity": 15,
    "quantity_fulfilled": 15,
    "price": "46.76",
    "offer_id": 52,
    "created_on": "18:06:17",
    "updated_at": "18:06:17"
    }
  ]

```
**Error Response**
**Code -** 401
**Content -** `{ error : "Trade was not successful" }`


 2.  `http://127.0.0.1:8000/v1/data_gateway/?code=bhel`


**Success Response -** 
**Code-** 200
**Content-** This endpoint returns a json object of the stock data(Truncated due to excess size) -
```json
{
    "data":
        {
        "symbol": "BHEL",
        "totalSellQuantity": 7332.0,
        "adhocMargin": 16.42,
        "companyName": "Bharat Heavy Electricals Limited",
        "marketType": "N",
        "dayHigh": 47.15,
        "basePrice": 46.55,
        "sellQuantity5": null,
        "sellQuantity4": null,
        "sellQuantity3": null,
        "sellQuantity2": null,
        "dayLow": 45.0,
        "sellQuantity1": 7332.0,
        "pChange": "-1.07",
        "buyPrice2": null,
        "buyPrice1": null,
        "previousClose": 46.55,
        "buyPrice4": null,
        "buyPrice3": null,
        "buyPrice5": null,
        "sellPrice1": 46.05,
        "sellPrice2": null,
        "sellPrice3": null,
        "sellPrice4": null,
        "sellPrice5": null,
        "change": "-0.50",
        "ndStartDate": null,
        "buyQuantity4": null,
        "buyQuantity3": null,
        "buyQuantity2": null,
        "buyQuantity1": null,
        "buyQuantity5": null,
        "closePrice": 46.05,
        "open": 46.5,
        "lastPrice": 46.05,
        "timestamp": "18:41:40"
        }
}
```
 
**Error Response**
**Code -** 401
**Content -** `{ error : "No stock of this code found" }`


The OB uses python sortedcontainers' sortedlist. Sortedlist is of the form:  `[ [quantity1, price1], [quantity2, price2], .... ]`. Asks and bids are stored in this list. The benefit of using sortedcontainers is that the accessing of element becomes extremely time efficient. Adding/removal also performs well on sortedcontainers as compared to B-Tree (Reference - [Link](grantjenks.com/docs/sortedcontainers/performance.html#id2)). Some time complexities are given below:

`add(value)` - Runtime complexity*: O(log(n)) – approximate.<br/>

`bisect_right(value)` - Runtime complexity*: O(log(n)) – approximate.

 The flow of order processing is shown below in the flow-diagram:
 
  
![order flow](https://github.com/ag602/mockstock/blob/master/stockex/static/images/documentation/flow.png?raw=true)


## Database Schema  
![db schema](https://github.com/ag602/mockstock/blob/master/stockex/static/images/documentation/temp.jpg?raw=true)
 