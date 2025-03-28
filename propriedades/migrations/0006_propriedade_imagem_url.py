# Generated by Django 5.0.1 on 2025-03-25 19:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('propriedades', '0005_propriedade_latitude_propriedade_longitude'),
    ]

    operations = [
        migrations.AddField(
            model_name='propriedade',
            name='imagem_url',
            field=models.URLField(blank=True, help_text='URL da imagem do imóvel no site da Caixa', max_length=500, null=True),
        ),
    ]
