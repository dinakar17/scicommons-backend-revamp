from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from ninja import File, Form, Router, UploadedFile
from ninja.errors import HttpError
from posts.models import SocialPost, SocialPostBookMark, SocialPostComment, SocialPostCommentLike, SocialPostLike, Hashtags
from users.auth import JWTAuth
from posts.schemas import PostResponseSchema, PostCreateSchema, PostCommentCreateSchema, PostCommentResponseSchema, PostByIdResponseSchema, HashtagResponseSchema, HashTagsListResponseSchema
from typing import Optional
from users.models import User

import json
from django.http import HttpResponse

router = Router(tags=["Posts"])

# CREATE POST API
@router.post("/create", auth=JWTAuth())
def create_post(request, details: PostCreateSchema, image_file: Optional[UploadedFile] = None):
    
    if not request.auth:
        raise HttpError(401, "You must be logged in to submit articles.")
    
    user = request.auth
    image_file = image_file if image_file else None
    hashtagsUsed = details.hashtags
    
    try:
        post = SocialPost.objects.create(
            user=user,
            body=details.body,
            image=image_file
        )

        if hashtagsUsed:
            for hashtag in hashtagsUsed:
                created_hashtag, created = Hashtags.objects.get_or_create(hashtag_name=hashtag)
                post.hashtag.add(created_hashtag)
            
        post.save()
                
        return {
            "id": post.id,
            "username": post.user.username,
            "body": post.body,
            "likes": 0, 
            "comments": 0, 
            "bookmarks": 0, 
            "created_at": post.created_at.isoformat()
        }
    except ValidationError as ve:
        raise HttpError(422, f"Validation error: {ve.message_dict}")
    except Exception as e:
        raise HttpError(500, f"Internal server error: {str(e)}")

# LIST POSTS API (WITH FILTER OPTION)
@router.get("/all", response=list[PostResponseSchema], auth=JWTAuth())
def list_posts(request, hashtag: Optional[str] = None):
    if hashtag:
        posts = SocialPost.objects.filter(hashtag__hashtag_name=hashtag).order_by("-created_at")
    else:
        posts = SocialPost.objects.all().order_by("-created_at")

    response = []
    for post in posts:
        response.append({
            "id": post.id,
            "username": post.user.username,
            "body": post.body,
            "likes": SocialPostLike.objects.filter(post=post).count(),
            "isLiked": SocialPostLike.objects.filter(user=request.auth, post=post).exists(),
            "comments": SocialPostComment.objects.filter(post=post).count(),
            "bookmarks": SocialPostBookMark.objects.filter(post=post).count(),
            "hashtags": [hashtag.hashtag_name for hashtag in post.hashtag.all()],
            "createdAt": post.created_at.isoformat()
        })
    return response

# GET POST API
@router.get("/{post_id}", response=PostByIdResponseSchema, auth=JWTAuth())
def get_post(request, post_id: int):
    post = get_object_or_404(SocialPost, id=post_id)
    post_comments = SocialPostComment.objects.filter(post=post)
    
    comment_dict = {}
    comments = []
    
    for comment in post_comments:
        comment_data = {
            "id": comment.id,
            "username": comment.user.username,
            "comment": comment.comment,
            "likes": SocialPostCommentLike.objects.filter(comment=comment).count(),
            "isLiked": SocialPostCommentLike.objects.filter(user=request.auth, comment=comment).exists(),
            "replies": [],
            "parentComment": comment.parent_comment_id,
            "postId": post_id,
            "createdAt": comment.created_at.isoformat()
        }
        
        comment_dict[comment.id] = comment_data
        
        if comment.parent_comment_id is None:
            comments.append(comment_data)
        else:
            parent_comment = comment_dict.get(comment.parent_comment_id)
            if parent_comment:
                parent_comment["replies"].append(comment_data)
    
    return {
        "id": post.id,
        "username": post.user.username,
        "body": post.body,
        "likes": SocialPostLike.objects.filter(post=post).count(),
        "isLiked": SocialPostLike.objects.filter(user=request.auth, post=post).exists(),
        "comments": comments,
        "bookmarks": SocialPostBookMark.objects.filter(post=post).count(),
        "hashtags": [hashtag.hashtag_name for hashtag in post.hashtag.all()],
        "createdAt": post.created_at.isoformat()
    }

# GET POSTS BY USER API
@router.get("/user/{username}", response=list[PostResponseSchema], auth=JWTAuth())
def get_posts_by_user(request, username: str):
    user = get_object_or_404(User, username=username)
    posts = SocialPost.objects.filter(user=user).order_by("likes")[:3]
    response = []
    for post in posts:
        response.append({
            "id": post.id,
            "username": post.user.username,
            "body": post.body,
            "likes": SocialPostLike.objects.filter(post=post).count(),
            "isLiked": SocialPostLike.objects.filter(user=request.auth, post=post).exists(),
            "comments": SocialPostComment.objects.filter(post=post).count(),
            "bookmarks": SocialPostBookMark.objects.filter(post=post).count(),
            "hashtags": [hashtag.hashtag_name for hashtag in post.hashtag.all()],
            "createdAt": post.created_at.isoformat()
        })
    return response

# UPDATE POST API
@router.put("/{post_id}", response=PostResponseSchema, auth=JWTAuth())
def update_post(request, post_id: int, details: Form[PostCreateSchema], image_file: File[UploadedFile] = None):
    post = get_object_or_404(SocialPost, id=post_id)
    if post.user != request.auth:
        raise HttpError(403, "You do not have permission to update this post.")
    
    image_file = image_file if image_file else None
    post.body = details.body
    post.image = image_file
    post.save()
    
    return {
        "id": post.id,
        "username": post.user.username,
        "body": post.body,
        "likes": SocialPostLike.objects.filter(post=post).count(),
        "isLiked": SocialPostLike.objects.filter(user=request.auth, post=post).exists(),
        "comments": SocialPostComment.objects.filter(post=post).count(),
        "bookmarks": SocialPostBookMark.objects.filter(post=post).count(),
        "hashtags": [hashtag.hashtag_name for hashtag in post.hashtag.all()],
        "createdAt": post.created_at.isoformat()
    }

# LIKE POST API
@router.get("/{post_id}/like", response=str, auth=JWTAuth())
def like_post(request, post_id: int):
    post = get_object_or_404(SocialPost, id=post_id)
    try:
        SocialPostLike.objects.get(user=request.auth, post=post)
        return HttpResponse(json.dumps({
            "message": "You have already liked this post.",
            "status": 400
        }), content_type="application/json", status=200)
    except SocialPostLike.DoesNotExist:
        SocialPostLike.objects.create(user=request.auth, post=post)
        return HttpResponse(json.dumps({
            "message": "Post liked successfully.",
            "status": 200
        }), content_type="application/json", status=200)
    
# UNLIKE POST API
@router.get("/{post_id}/unlike", response=str, auth=JWTAuth())
def unlike_post(request, post_id: int):
    post = get_object_or_404(SocialPost, id=post_id)
    like = SocialPostLike.objects.filter(user=request.auth, post=post)
    
    if post and like.exists():
        like.delete()
        return HttpResponse(json.dumps({
            "message": "Post unliked successfully.",
            "status": 200
        }), content_type="application/json", status=200)
    else:
        return HttpResponse(json.dumps({
            "message": "You have not liked this post.",
            "status": 400
        }), content_type="application/json", status=200)

# BOOKMARK POST API
@router.post("/{post_id}/bookmark", response=str, auth=JWTAuth())
def bookmark_post(request, post_id: int):
    post = get_object_or_404(SocialPost, id=post_id)
    try:
        SocialPostBookMark.objects.create(user=request.auth, post=post)
        return "Post bookmarked successfully."
    except IntegrityError:
        raise HttpError(400, "You have already bookmarked this post.")

# UNBOOKMARK POST API
@router.post("/{post_id}/unbookmark", response=str, auth=JWTAuth())
def unbookmark_post(request, post_id: int):
    post = get_object_or_404(SocialPost, id=post_id)
    bookmark = SocialPostBookMark.objects.filter(user=request.auth, post=post)
    if bookmark.exists():
        bookmark.delete()
        return "Post unbookmarked successfully."
    else:
        raise HttpError(400, "You have not bookmarked this post.")

# COMMENT ON POST API
@router.post("/{post_id}/comment", response=PostCommentResponseSchema, auth=JWTAuth())
def comment_on_post(request, post_id: int, details: PostCommentCreateSchema):
    post = get_object_or_404(SocialPost, id=post_id)
    comment = SocialPostComment.objects.create(
        user=request.auth,
        post=post,
        comment=details.comment,
        parent_comment_id=details.parentComment
    )
    return {
        "id": comment.id,
        "username": comment.user.username,
        "comment": comment.comment,
        "likes": 0,
        "isLiked": False,
        "replies": [],
        "parentComment": comment.parent_comment_id,
        "postId": post_id,
        "createdAt": comment.created_at.isoformat()
    }

# LIST COMMENTS API
@router.get("/{post_id}/comments", response=list[PostCommentResponseSchema], auth=JWTAuth())
def list_comments(request, post_id: int):
    post = get_object_or_404(SocialPost, id=post_id)
    comments = SocialPostComment.objects.filter(post=post)
    response = []
    for comment in comments:
        response.append({
            "id": comment.id,
            "username": comment.user.username,
            "comment": comment.comment,
            "likes": SocialPostCommentLike.objects.filter(comment=comment).count(),
            "replies": SocialPostComment.objects.filter(parent_comment=comment),
            "parentComment": comment.parent_comment_id,
            "postId": post_id,
            "createdAt": comment.created_at.isoformat()
        })
    return response

# LIKE COMMENT API
@router.get("/comment/{comment_id}/like", response=str, auth=JWTAuth())
def like_comment(request, comment_id: int):
    comment = get_object_or_404(SocialPostComment, id=comment_id)
    try:
        SocialPostCommentLike.objects.get(user=request.auth, comment=comment)
        return HttpResponse(json.dumps({
            "message": "You have already liked this comment.",
            "status": 400
        }), content_type="application/json", status=200)
    except SocialPostCommentLike.DoesNotExist:
        SocialPostCommentLike.objects.create(user=request.auth, comment=comment)
        return HttpResponse(json.dumps({
            "message": "Comment liked successfully.",
            "status": 200
        }), content_type="application/json", status=200)

# UNLIKE COMMENT API
@router.get("/comment/{comment_id}/unlike", response=str, auth=JWTAuth())
def unlike_comment(request, comment_id: int):
    comment = get_object_or_404(SocialPostComment, id=comment_id)
    like = SocialPostCommentLike.objects.filter(user=request.auth, comment=comment)
    if comment and like.exists():
        like.delete()
        return HttpResponse(json.dumps({
            "message": "Comment unliked successfully.",
            "status": 200
        }), content_type="application/json", status=200)
    else:
        return HttpResponse(json.dumps({
            "message": "You have not liked this comment.",
            "status": 400
        }), content_type="application/json", status=200)

# GET COMMENT API
@router.get("/{post_id}/comments/{comment_id}", response=PostCommentResponseSchema, auth=JWTAuth())
def get_comment(request, post_id: int, comment_id: int):
    comment = get_object_or_404(SocialPostComment, id=comment_id)
    return {
        "id": comment.id,
        "username": comment.user.username,
        "comment": comment.comment,
        "likes": SocialPostCommentLike.objects.filter(comment=comment).count(),
        "replies": SocialPostComment.objects.filter(parent_comment=comment),
        "createdAt": comment.created_at.isoformat(),
        "parentComment": comment.parent_comment_id,
        "postId": post_id
    }

# REPLY TO COMMENT API
@router.post("/{post_id}/comments/{comment_id}/reply", response=PostCommentResponseSchema, auth=JWTAuth())
def reply_to_comment(request, post_id: int, comment_id: int, details: Form[PostCommentCreateSchema]):
    comment = get_object_or_404(SocialPostComment, id=comment_id)
    post = get_object_or_404(SocialPost, id=post_id)
    reply = SocialPostComment.objects.create(
        user=request.auth,
        post=post,
        comment=details.comment,
        parent_comment=comment
    )
    return {
        "id": reply.id,
        "username": reply.user.username,
        "comment": reply.comment,
        "likes": 0,
        "replies": [],
        "parentComment": reply.parent_comment_id,
        "postId": post_id,
        "createdAt": reply.created_at.isoformat()
    }

# DELETE POST API
@router.delete("/{post_id}", response=str, auth=JWTAuth())
def delete_post(request, post_id: int):
    post = get_object_or_404(SocialPost, id=post_id)
    if post.user != request.auth:
        raise HttpError(403, "You do not have permission to delete this post.")
    post.delete()
    return "Post deleted successfully."

# DELETE COMMENT API
@router.delete("/{post_id}/comments/{comment_id}", response=str, auth=JWTAuth())
def delete_comment(request, post_id: int, comment_id: int):
    comment = get_object_or_404(SocialPostComment, id=comment_id)
    if comment.user != request.auth:
        raise HttpError(403, "You do not have permission to delete this comment.")
    comment.delete()
    return "Comment deleted successfully."

# DELETE REPLY API
@router.delete("/{post_id}/comments/{comment_id}/replies/{reply_id}", response=str, auth=JWTAuth())
def delete_reply(request, post_id: int, comment_id: int, reply_id: int):
    reply = get_object_or_404(SocialPostComment, id=reply_id)
    if reply.user != request.auth:
        raise HttpError(403, "You do not have permission to delete this reply.")
    reply.delete()
    return "Reply deleted successfully."

# COMMENT THREAD FROM REPLY ID API
def get_comment_thread(comment_id: int) -> list[dict]:
    thread = []
    current_comment = get_object_or_404(SocialPostComment, id=comment_id)
    
    while current_comment:
        thread.append({
            "id": current_comment.id,
            "username": current_comment.user.username,
            "comment": current_comment.comment,
            "likes": SocialPostCommentLike.objects.filter(comment=current_comment).count(),
            "replies": SocialPostComment.objects.filter(parent_comment=current_comment).count(),
            "createdAt": current_comment.created_at.isoformat()
        })
        current_comment = current_comment.parent_comment
    
    return thread[::-1]  # Reverse to start from the root parent

@router.get("/{post_id}/comments/{comment_id}/replies/{reply_id}/thread", response=list[PostCommentResponseSchema], auth=JWTAuth())
def comment_thread(request, post_id: int, comment_id: int, reply_id: int):
    response = get_comment_thread(reply_id)
    return response

# List all hashtags
@router.get("/get/hashtags", response=HashTagsListResponseSchema, auth=JWTAuth())
def list_hashtags(request):
    hashtags = Hashtags.objects.all()
    response = []
    for hashtag in hashtags:
        response.append({
            "id": hashtag.id,
            "hashtag": f"#{hashtag.hashtag_name}",
            "totalPosts": hashtag.post.count()
        })
    return {"hashtags": response}