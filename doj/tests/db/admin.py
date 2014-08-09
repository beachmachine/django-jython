# -*- coding: utf-8 -*-

from django.contrib import admin

from doj.tests.db.models import TestModel, TestModelRelation


admin.site.register(TestModel)
admin.site.register(TestModelRelation)