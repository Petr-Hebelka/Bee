# Generated by Django 4.2.7 on 2025-02-03 18:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mothers',
            name='hive',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='myapp.hives', unique=True),
        ),
    ]
