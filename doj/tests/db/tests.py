# -*- coding: utf-8 -*-

from datetime import datetime

from django.test import TestCase

from doj.tests.db.models import TestModel, TestModelRelation


class DBTestCase(TestCase):
    NUMBER_OF_RECORDS = 10
    NUMBER_OF_RELATIONS = 2

    def setUp(self):
        TestModel.objects.all().delete()
        TestModelRelation.objects.all().delete()

    def test_inserting_records(self):
        for _ in range(0, DBTestCase.NUMBER_OF_RECORDS):
            TestModel().save()

        self.assertEqual(TestModel.objects.all()[0].field_4, 'abc')
        self.assertEqual(TestModel.objects.all().count(), DBTestCase.NUMBER_OF_RECORDS)

    def test_inserting_relations(self):
        test_relation = TestModelRelation()
        test_relation.save()

        for _ in range(0, DBTestCase.NUMBER_OF_RELATIONS):
            test_model = TestModel()
            test_model.save()
            test_relation.test_models.add(test_model)

        self.assertEqual(test_relation.test_models.all()[0].field_4, 'abc')
        self.assertEqual(test_relation.test_models.all().count(), DBTestCase.NUMBER_OF_RELATIONS)

    def test_related_lookup(self):
        test_model = None

        test_relation = TestModelRelation()
        test_relation.save()

        for _ in range(0, DBTestCase.NUMBER_OF_RELATIONS):
            test_model = TestModel()
            test_model.save()
            test_relation.test_models.add(test_model)

        test_model = TestModel.objects.select_related('field_19').get(id=test_model.id)

        self.assertEqual(test_model.field_19.field_1, 1234)

    def test_limit_related_lookup(self):
        for _ in range(0, DBTestCase.NUMBER_OF_RECORDS):
            test_model = TestModel()
            test_model.save()

            test_relation = TestModelRelation()
            test_relation.save()

            test_relation.test_models.add(test_model)

        test_models = TestModel.objects.select_related('field_19').all()[2:4]

        self.assertEqual(len(test_models), 2)

    def test_datetime_lookup(self):
        past_date = datetime(1999, 1, 1)
        future_date = datetime(2999, 2, 2)

        for _ in range(0, DBTestCase.NUMBER_OF_RECORDS/2):
            test_model = TestModel()
            test_model.save()

            test_model.field_5 = past_date
            test_model.save()

        for _ in range(0, DBTestCase.NUMBER_OF_RECORDS/2):
            test_model = TestModel()
            test_model.save()

            test_model.field_5 = future_date
            test_model.save()

        self.assertEqual(TestModel.objects.filter(field_5__year=past_date.year).count(), DBTestCase.NUMBER_OF_RECORDS/2)
        self.assertEqual(TestModel.objects.filter(field_5__month=past_date.month).count(), DBTestCase.NUMBER_OF_RECORDS/2)
        self.assertEqual(TestModel.objects.filter(field_5__day=past_date.day).count(), DBTestCase.NUMBER_OF_RECORDS/2)
        self.assertEqual(TestModel.objects.filter(field_5__lt=future_date).count(), DBTestCase.NUMBER_OF_RECORDS/2)
        self.assertEqual(TestModel.objects.filter(field_5__gt=past_date).count(), DBTestCase.NUMBER_OF_RECORDS/2)
        self.assertEqual(TestModel.objects.filter(field_5__range=(past_date, future_date)).count(), DBTestCase.NUMBER_OF_RECORDS)