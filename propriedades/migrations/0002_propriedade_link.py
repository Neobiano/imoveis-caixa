# Generated by Django 5.0.1 on 2025-03-25 02:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('propriedades', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='propriedade',
            name='link',
            field=models.URLField(blank=True, null=True),
        ),
    ]
