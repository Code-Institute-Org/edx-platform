# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ci_program', '0006_auto_20180620_1017'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentEnrollment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_of_enrollment', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AlterField(
            model_name='program',
            name='enrolled_students',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='studentenrollment',
            name='program',
            field=models.ForeignKey(to='ci_program.Program'),
        ),
        migrations.AddField(
            model_name='studentenrollment',
            name='student',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
    ]
