# Generated by Django 4.2.7 on 2025-02-17 11:46

from django.db import migrations
import myapp.models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0014_visits_comment_alter_visits_hive_body_size_and_more'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='beekeepers',
            managers=[
                ('objects', myapp.models.BeekeepersManager()),
            ],
        ),
    ]
