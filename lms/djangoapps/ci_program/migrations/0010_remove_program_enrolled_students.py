# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ci_program', '0009_auto_20180719_0913'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='program',
            name='enrolled_students',
        ),
    ]
