# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ci_program', '0007_auto_20180620_1027'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentProgramEnrollment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('is_active', models.BooleanField()),
            ],
            options={
                'ordering': ('-modified', '-created'),
                'abstract': False,
                'get_latest_by': 'modified',
            },
        ),
        migrations.RemoveField(
            model_name='studentenrollment',
            name='program',
        ),
        migrations.RemoveField(
            model_name='studentenrollment',
            name='student',
        ),
        migrations.RemoveField(
            model_name='program',
            name='enrolled_students',
        ),
        migrations.RemoveField(
            model_name='program',
            name='zoho_program_code',
        ),
        migrations.DeleteModel(
            name='StudentEnrollment',
        ),
        migrations.AddField(
            model_name='studentprogramenrollment',
            name='program',
            field=models.ForeignKey(to='ci_program.Program'),
        ),
        migrations.AddField(
            model_name='studentprogramenrollment',
            name='student',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
    ]
