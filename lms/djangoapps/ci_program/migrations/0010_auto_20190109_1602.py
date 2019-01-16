# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ci_program', '0009_merge'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studentprogramenrollment',
            name='program',
        ),
        migrations.RemoveField(
            model_name='studentprogramenrollment',
            name='student',
        ),
        migrations.AddField(
            model_name='program',
            name='enrolled_students',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.DeleteModel(
            name='StudentProgramEnrollment',
        ),
    ]
