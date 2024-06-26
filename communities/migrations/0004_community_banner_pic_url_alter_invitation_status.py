# Generated by Django 5.0.4 on 2024-06-15 13:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("communities", "0003_remove_communitypost_author_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="community",
            name="banner_pic_url",
            field=models.FileField(null=True, upload_to="community_images/"),
        ),
        migrations.AlterField(
            model_name="invitation",
            name="status",
            field=models.CharField(
                choices=[
                    ("accepted", "Accepted"),
                    ("pending", "Pending"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                max_length=10,
            ),
        ),
    ]
