# -*- coding: utf-8 -*-

from django.contrib import admin

from doj.tests.db.models import TestModel, TestModelRelation

admin.register(TestModel)
admin.register(TestModelRelation)