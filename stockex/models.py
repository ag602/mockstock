from djongo import models


# from django.contrib.auth.models import User
# Create your models here.

# class CommonInfo(models.Model):
#     """
#     Abstract class acts like a base to other models with common fields
#     """
#     created_on = models.CharField()
#     updated_at = models.CharField()
#
#     class Meta:
#         abstract = True
# class Items(models.Model):
#     code = models.CharField(max_length=10)
#     name = models.CharField(max_length=255)
#     details = models.TextField()
#     total_shares = models.IntegerField()
#     rem_shares = models.IntegerField()
#     price = models.IntegerField()
#     created_on = models.CharField(max_length=15)
#     updated_at = models.CharField(max_length=15)
#
#     def __str__(self):
#         return self.name


class Offer(models.Model):
    user_id = models.IntegerField()
    item_id = models.IntegerField()
    code = models.CharField(max_length=15)
    companyName = models.CharField(max_length=50)
    quantity = models.IntegerField()
    type = models.CharField(default="market", max_length=4)
    direction = models.CharField(default="buy", max_length=4)
    limit_price = models.CharField(max_length=15, default=0)
    price = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    created_on = models.CharField(max_length=15)
    updated_at = models.CharField(max_length=15)

    def __str__(self):
        return ("Uid:%s | Code:%s | Created:%s") % (self.user_id, self.code, self.created_on)


class Trade(models.Model):
    item_id = models.IntegerField()
    seller_id = models.IntegerField()
    buyer_id = models.IntegerField()
    quantity = models.IntegerField()
    quantity_fulfilled = models.IntegerField()
    price = models.CharField(max_length=10, default=0)
    offer_id = models.IntegerField()
    created_on = models.CharField(max_length=15)
    updated_at = models.CharField(max_length=15)


class Bids(models.Model):
    buy_price = models.CharField(max_length=10)
    buy_quantity = models.IntegerField()


class Asks(models.Model):
    sell_price = models.CharField(max_length=10)
    sell_quantity = models.IntegerField()


class OrderBook(models.Model):
    item_id = models.IntegerField()
    asks = models.ManyToManyField(to=Asks, related_name='ask', blank=True)
    bids = models.ManyToManyField(to=Bids, related_name='buy', blank=True)





