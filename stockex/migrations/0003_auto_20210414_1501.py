# Generated by Django 2.2 on 2021-04-14 09:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stockex', '0002_delete_orderbook'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='direction',
            field=models.CharField(default='Buy', max_length=4),
        ),
        migrations.AlterField(
            model_name='offer',
            name='type',
            field=models.CharField(default='market', max_length=4),
        ),
    ]
