from enum import Enum
from typing import List, Optional

from django.contrib.contenttypes.models import ContentType
from ninja import Query, Router
from ninja.responses import codes_4xx, codes_5xx

# Todo: Move the Reaction model to the users app
from articles.models import Article, Reaction
from articles.schemas import ArticleDetails
from users.auth import JWTAuth, OptionalJWTAuth
from users.models import Notification, User
from users.schemas import (
    ContentTypeEnum,
    Message,
    NotificationSchema,
    ReactionCountOut,
    ReactionIn,
    ReactionOut,
    VoteEnum,
)

router = Router(tags=["Users"])


class StatusFilter(str, Enum):
    UNSUBMITTED = "unsubmitted"
    PUBLISHED = "published"


# Get my articles
@router.get(
    "/my-articles",
    response={200: List[ArticleDetails], codes_4xx: Message, codes_5xx: Message},
    auth=JWTAuth(),
)
def get_my_articles(request, status_filter: Optional[StatusFilter] = Query(None)):
    try:
        articles = Article.objects.filter(submitter=request.auth).order_by(
            "-created_at"
        )

        if status_filter == StatusFilter.PUBLISHED:
            articles = articles.filter(published=True)
        elif status_filter == StatusFilter.UNSUBMITTED:
            articles = articles.filter(status="Pending", community=None)

        return 200, articles
    except Exception as e:
        return 500, {"message": str(e)}


def get_content_type(content_type_value: str) -> ContentType:
    app_label, model = content_type_value.split(".")
    return ContentType.objects.get(app_label=app_label, model=model)


@router.post(
    "/reactions",
    response={200: Message, codes_4xx: Message, codes_5xx: Message},
    auth=JWTAuth(),
)
def post_reaction(request, reaction: ReactionIn):
    content_type = get_content_type(reaction.content_type.value)

    existing_reaction = Reaction.objects.filter(
        user=request.auth, content_type=content_type, object_id=reaction.object_id
    ).first()

    if existing_reaction:
        if existing_reaction.vote == reaction.vote.value:
            # User is clicking the same reaction type, so remove it
            existing_reaction.delete()
            return ReactionOut(
                id=None,
                user_id=request.auth.id,
                vote=None,
                created_at=None,
                message="Reaction removed",
            )
        else:
            # User is changing their reaction from like to dislike or vice versa
            existing_reaction.vote = reaction.vote.value
            existing_reaction.save()
            return ReactionOut(
                id=existing_reaction.id,
                user_id=existing_reaction.user_id,
                vote=VoteEnum(existing_reaction.vote),
                created_at=existing_reaction.created_at.isoformat(),
                message="Reaction updated",
            )
    else:
        # User is reacting for the first time
        new_reaction = Reaction.objects.create(
            user=request.auth,
            content_type=content_type,
            object_id=reaction.object_id,
            vote=reaction.vote.value,
        )
        return ReactionOut(
            id=new_reaction.id,
            user_id=new_reaction.user_id,
            vote=VoteEnum(new_reaction.vote),
            created_at=new_reaction.created_at.isoformat(),
            message="Reaction added",
        )


@router.get(
    "/reaction_count/{content_type}/{object_id}/",
    response=ReactionCountOut,
    auth=OptionalJWTAuth,
)
def get_reaction_count(request, content_type: ContentTypeEnum, object_id: int):
    content_type = get_content_type(content_type.value)

    reactions = Reaction.objects.filter(content_type=content_type, object_id=object_id)

    likes = reactions.filter(vote=VoteEnum.LIKE.value).count()
    dislikes = reactions.filter(vote=VoteEnum.DISLIKE.value).count()

    # Check if the authenticated user is the author
    current_user: Optional[User] = None if not request.auth else request.auth
    user_reaction = None

    if current_user:
        user_reaction_obj = reactions.filter(user=current_user).first()
        if user_reaction_obj:
            user_reaction = VoteEnum(user_reaction_obj.vote)

    return ReactionCountOut(
        likes=likes,
        dislikes=dislikes,
        user_reaction=user_reaction,
    )


@router.get(
    "/notifications",
    response={200: List[NotificationSchema], codes_4xx: Message, codes_5xx: Message},
    auth=JWTAuth(),
)
def get_notifications(request):
    try:
        user_notifications = Notification.objects.filter(user=request.auth).order_by(
            "-created_at"
        )

        return 200, [
            NotificationSchema(
                **{
                    "id": notif.id,
                    "message": notif.message,
                    "content": notif.content,
                    "isRead": notif.is_read,
                    "link": notif.link,
                    "category": notif.category,
                    "notificationType": notif.notification_type,
                    "createdAt": notif.created_at,
                    "expiresAt": notif.expires_at,
                }
            )
            for notif in user_notifications
        ]
    except Exception as e:
        return 500, {"message": str(e)}


@router.post(
    "/notifications/{notification_id}/mark-as-read",
    response={200: Message, codes_4xx: Message, codes_5xx: Message},
    auth=JWTAuth(),
)
def mark_notification_as_read(request, notification_id: int):
    try:
        notification = Notification.objects.get(pk=notification_id, user=request.auth)
        if not notification:
            return 404, {"message": "Notification does not exist."}

        if not notification.is_read:
            notification.is_read = True
            notification.save()
            return {"message": "Notification marked as read."}
        else:
            return {"message": "Notification was already marked as read."}
    except Exception as e:
        return 500, {"message": str(e)}
