# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ci_program', '0008_merge'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studentenrollment',
            name='program',
        ),
        migrations.RemoveField(
            model_name='studentenrollment',
            name='student',
        ),
        migrations.DeleteModel(
            name='StudentEnrollment',
        ),
    ]
