from django.db import models
from users.models import User

class SocialPost(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField(max_length=2000)
    image = models.FileField(upload_to="social_post_images/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "social_post"

    def __str__(self):
        return self.body

class SocialPostComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(
        SocialPost, on_delete=models.CASCADE, related_name="comments"
    )
    comment = models.TextField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    parent_comment = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )

    class Meta:
        db_table = "social_post_comment"

    def __str__(self):
        return self.comment

class SocialPostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        db_table = "social_post_like"

    def __str__(self):
        return str(self.id)

class SocialPostCommentLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(
        SocialPostComment, on_delete=models.CASCADE, related_name="likes"
    )
    # post = models.ForeignKey(SocialPost, on_delete=models.CASCADE)

    class Meta:
        db_table = "social_post_comment_like"

    def __str__(self):
        return str(self.id)

class SocialPostBookMark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE)

    class Meta:
        db_table = 'social_post_bookmark'
        unique_together = ['user','post']

    def __str__(self):
        return str(self.id)
    
class Hashtags(models.Model):
    hashtag_name = models.CharField(max_length=50, unique=True)
    post = models.ManyToManyField(SocialPost, related_name="hashtag")

    class Meta:
        db_table = "hashtag"

    def __str__(self):
        return self.hashtag_name