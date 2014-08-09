# -*- coding: utf-8 -*-

from datetime import datetime

from django.test import TestCase
from django.db.models import Count, Min, Max, Avg, Sum
from django.db.models.query import EmptyQuerySet

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

    def test_join_lookup(self):
        for _ in range(0, DBTestCase.NUMBER_OF_RECORDS):
            test_model = TestModel()
            test_model.save()

            test_relation = TestModelRelation()
            test_relation.save()

            test_relation.test_models.add(test_model)

        self.assertEqual(TestModel.objects.filter(field_19__field_1=1234).count(), DBTestCase.NUMBER_OF_RECORDS)
        self.assertEqual(TestModel.objects.filter(field_19__field_1=0).count(), 0)

    def test_bulk_create(self):
        TestModel.objects.bulk_create(
            [TestModel() for _ in range(0, DBTestCase.NUMBER_OF_RECORDS)]
        )

        self.assertEqual(TestModel.objects.all().count(), DBTestCase.NUMBER_OF_RECORDS)

    def test_bulk_update(self):
        for _ in range(0, DBTestCase.NUMBER_OF_RECORDS):
            test_model = TestModel()
            test_model.save()

        TestModel.objects.all().update(field_4='xyz')

        self.assertEqual(TestModel.objects.filter(field_4='xyz').count(), DBTestCase.NUMBER_OF_RECORDS)
        self.assertEqual(TestModel.objects.filter(field_4='abc').count(), 0)

    def test_latest_earliest(self):
        for _ in range(0, DBTestCase.NUMBER_OF_RECORDS):
            test_model = TestModel()
            test_model.save()

        latest = TestModel.objects.latest('field_18')
        earliest = TestModel.objects.earliest('field_18')

        self.assertIsInstance(latest, TestModel)
        self.assertIsInstance(earliest, TestModel)

    def test_first_last(self):
        for _ in range(0, DBTestCase.NUMBER_OF_RECORDS):
            test_model = TestModel()
            test_model.save()

        first = TestModel.objects.order_by('id').first()
        last = TestModel.objects.order_by('id').last()

        self.assertIsInstance(first, TestModel)
        self.assertIsInstance(last, TestModel)

    def test_aggregate(self):
        counter = 1
        counters = []
        for _ in range(0, DBTestCase.NUMBER_OF_RECORDS):
            test_model = TestModel(field_10=counter)
            test_model.save()

            counters.append(counter)
            counter += 1

        count_result = TestModel.objects.aggregate(Count('field_10'))
        avg_result = TestModel.objects.aggregate(Avg('field_10'))
        min_result = TestModel.objects.aggregate(Min('field_10'))
        max_result = TestModel.objects.aggregate(Max('field_10'))
        sum_result = TestModel.objects.aggregate(Sum('field_10'))

        self.assertEqual(count_result, {'field_10__count': DBTestCase.NUMBER_OF_RECORDS})
        self.assertEqual(min_result, {'field_10__min': 1})
        self.assertEqual(max_result, {'field_10__max': DBTestCase.NUMBER_OF_RECORDS})
        self.assertEqual(avg_result, {'field_10__avg': float(sum(counters))/len(counters)})
        self.assertEqual(sum_result, {'field_10__sum': sum(counters)})

    def test_none(self):
        for _ in range(0, DBTestCase.NUMBER_OF_RECORDS):
            test_model = TestModel()
            test_model.save()

        self.assertEqual(TestModel.objects.none().count(), 0)
        self.assertIsInstance(TestModel.objects.none(), EmptyQuerySet)