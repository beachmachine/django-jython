# -*- coding: utf-8 -*-

from django.db import models


class TestModel(models.Model):

    field_1 = models.BigIntegerField(default=9223372036854775807)
    field_2 = models.BinaryField(default="010101010101010101010101")  # Causes problems with SQLite
    field_3 = models.BooleanField(default=True)
    field_4 = models.CharField(max_length=256, default="abc")
    field_5 = models.DateField(auto_now_add=True)
    field_6 = models.DateTimeField(auto_now_add=True)
    field_7 = models.DecimalField(max_digits=5, decimal_places=2, default=123.45)
    field_8 = models.EmailField(default='test@email.at')
    field_9 = models.FloatField(default=12.34)
    field_10 = models.IntegerField(default=1234)
    field_11 = models.GenericIPAddressField(default='192.0.2.30')
    field_12 = models.NullBooleanField(default=None)
    field_13 = models.PositiveIntegerField(default=1234)
    field_14 = models.PositiveSmallIntegerField(default=1234)
    field_15 = models.SmallIntegerField(default=1234)
    field_16 = models.TextField(default="abc")
    field_18 = models.TimeField(auto_now_add=True)
    field_19 = models.ForeignKey('TestModelRelation', related_name='test_models', null=True, blank=True)


class TestModelRelation(models.Model):

    field_1 = models.BigIntegerField(default=1234)