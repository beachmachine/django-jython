# -*- coding: utf-8 -*-

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

        self.assertEqual(TestModel.objects.all().count(), DBTestCase.NUMBER_OF_RECORDS)

        TestModel.objects.all().delete()

    def test_inserting_relations(self):
        test_relation = TestModelRelation()
        test_relation.save()

        for _ in range(0, DBTestCase.NUMBER_OF_RELATIONS):
            test_model = TestModel()
            test_model.save()
            test_relation.test_models.add(test_model)

        self.assertEqual(test_relation.test_models.all().count(), DBTestCase.NUMBER_OF_RELATIONS)

        TestModel.objects.all().delete()
        TestModelRelation.objects.all().delete()

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

        TestModel.objects.all().delete()
        TestModelRelation.objects.all().delete()