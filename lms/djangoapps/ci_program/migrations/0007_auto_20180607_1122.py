# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('ci_program', '0006_auto_20180517_0933'),
    ]

    operations = [
        migrations.AlterField(
            model_name='program',
            name='enrolled_students',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, blank=True),
        ),
    ]
