# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student_enrollment', '0003_auto_20180601_0942'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='programaccessstatus',
            name='user',
        ),
        migrations.DeleteModel(
            name='ProgramAccessStatus',
        ),
    ]
