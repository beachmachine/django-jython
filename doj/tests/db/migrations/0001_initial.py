# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TestModel',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, help_text='', verbose_name='ID', primary_key=True)),
                ('field_1', models.BigIntegerField(help_text='', default=9223372036854775807L)),
                ('field_2', models.BinaryField(editable=False, help_text='', default=b'010101010101010101010101')),
                ('field_3', models.BooleanField(help_text='', default=True)),
                ('field_4', models.CharField(max_length=256, help_text='', default=b'abc')),
                ('field_5', models.DateField(help_text='', auto_now_add=True)),
                ('field_6', models.DateTimeField(help_text='', auto_now_add=True)),
                ('field_7', models.DecimalField(help_text='', max_digits=5, decimal_places=2, default=123.45)),
                ('field_8', models.EmailField(max_length=75, help_text='', default=b'test@email.at')),
                ('field_9', models.FloatField(help_text='', default=12.34)),
                ('field_10', models.IntegerField(help_text='', default=1234)),
                ('field_11', models.GenericIPAddressField(help_text='', default=b'192.0.2.30')),
                ('field_12', models.NullBooleanField(help_text='', default=None)),
                ('field_13', models.PositiveIntegerField(help_text='', default=1234)),
                ('field_14', models.PositiveSmallIntegerField(help_text='', default=1234)),
                ('field_15', models.SmallIntegerField(help_text='', default=1234)),
                ('field_16', models.TextField(help_text='', default=b'abc')),
                ('field_18', models.TimeField(editable=False, help_text='', blank=True, auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TestModelRelation',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, help_text='', verbose_name='ID', primary_key=True)),
                ('field_1', models.BigIntegerField(help_text='', default=1234)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='testmodel',
            name='field_19',
            field=models.ForeignKey(help_text='', to='db.TestModelRelation', null=True, blank=True),
            preserve_default=True,
        ),
    ]
