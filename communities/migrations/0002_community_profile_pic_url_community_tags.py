# Generated by Django 5.0.4 on 2024-06-03 14:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("communities", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="community",
            name="profile_pic_url",
            field=models.FileField(null=True, upload_to="community_images/"),
        ),
        migrations.AddField(
            model_name="community",
            name="tags",
            field=models.JSONField(default=list),
        ),
    ]
