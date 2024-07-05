from typing import List, Optional
from ninja import Schema
from datetime import datetime

class PostCreateSchema(Schema):
    body: str
    image: Optional[str] = None
    hashtags: Optional[List[str]] = None
    createdAt: str = datetime.now().isoformat()

class PostResponseSchema(Schema):
    id: int
    username: str
    body: str
    likes: int
    isLiked: bool
    comments: int
    bookmarks: int
    hashtags: list
    createdAt: str

class PostByIdResponseSchema(Schema):
    id: int
    username: str
    body: str
    image: Optional[str] = None
    likes: int
    isLiked: bool
    comments: list
    bookmarks: int
    hashtags: list
    createdAt: str

class PostCommentCreateSchema(Schema):
    comment: str
    parentComment: Optional[int] = None
    createdAt: str = datetime.now().isoformat()

class PostCommentResponseSchema(Schema):
    id: int
    username: str
    comment: str
    likes: int
    isLiked: bool
    replies: list
    createdAt: str
    postId: int
    parentComment: Optional[int] = None

class PostCommentLikeUnlikeRequestSchema(Schema):
    commentId: int

class HashtagResponseSchema(Schema):
    id: int
    hashtag: str
    totalPosts: int

class HashTagsListResponseSchema(Schema):
    hashtags: List[HashtagResponseSchema]