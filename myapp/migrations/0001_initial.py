# Generated by Django 4.2.7 on 2025-02-03 16:40

from django.conf import settings
import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Beekeepers',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('beekeeper_id', models.IntegerField(unique=True)),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            bases=('auth.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Hives',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.IntegerField()),
                ('type', models.CharField(max_length=255)),
                ('size', models.IntegerField()),
                ('comment', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Tasks',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Visits',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('inspection_type', models.CharField(max_length=255)),
                ('condition', models.IntegerField()),
                ('hive_body_size', models.CharField(max_length=255)),
                ('honey_supers_size', models.CharField(max_length=255)),
                ('honey_yield', models.FloatField()),
                ('medication_application', models.CharField(max_length=255)),
                ('disease', models.CharField(max_length=255)),
                ('mite_drop', models.IntegerField()),
                ('hive', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='myapp.hives')),
                ('performed_tasks', models.ManyToManyField(blank=True, to='myapp.tasks')),
            ],
        ),
        migrations.CreateModel(
            name='Mothers',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mark', models.CharField(max_length=255, unique=True)),
                ('year', models.IntegerField()),
                ('male_line', models.CharField(max_length=255)),
                ('female_line', models.CharField(max_length=255)),
                ('comment', models.TextField()),
                ('ancestor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='myapp.mothers')),
                ('hive', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='myapp.hives')),
            ],
        ),
        migrations.CreateModel(
            name='HivesPlaces',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('type', models.CharField(max_length=255)),
                ('location', models.CharField(max_length=255)),
                ('comment', models.TextField()),
                ('beekeeper', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.beekeepers')),
            ],
        ),
        migrations.AddField(
            model_name='hives',
            name='place',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.hivesplaces'),
        ),
    ]
