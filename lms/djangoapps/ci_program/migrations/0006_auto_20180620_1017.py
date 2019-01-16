# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ci_program', '0005_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='program',
            name='program_code',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.RemoveField(
            model_name='program',
            name='number_of_modules',
        ),
        migrations.AddField(
            model_name='program',
            name='program_code_friendly_name',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
    ]
