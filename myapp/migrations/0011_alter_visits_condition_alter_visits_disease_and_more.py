# Generated by Django 4.2.7 on 2025-02-09 10:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0010_remove_hives_unique_place_hive_number_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visits',
            name='condition',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='visits',
            name='disease',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='visits',
            name='hive_body_size',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='visits',
            name='honey_supers_size',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='visits',
            name='honey_yield',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='visits',
            name='medication_application',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='visits',
            name='mite_drop',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
