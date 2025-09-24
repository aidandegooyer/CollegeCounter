from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1420471133488021546/ZmUPidHr54isrBj_-8mRsgqsyO7y3Cn0tfMC2VrkI5wdXjf20awDVt1kOkPMO0ADJcsn"


class SanityWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        try:
            payload = request.data

            # Pull values from projection you set in Sanity webhook
            doc_id = payload.get("_id")
            doc_type = payload.get("_type")
            title = payload.get("title", "Untitled")
            slug = payload.get("slug")
            author = payload.get("author", "Unknown")
            author_link = payload.get("authorLink")
            published_at = payload.get("publishedAt")
            image_url = payload.get("imageUrl")

            # Build article URL
            article_url = f"https://collegecounter.org/news/{slug}" if slug else None

            embed = {
                "title": f"📝 {title}",
                "url": article_url,  # Makes the title clickable
                "description": (
                    f"A new article has been published by [{author}]({author_link})"
                    if author_link
                    else f"A new article has been published by **{author}**."
                ),
                "color": 0x00FF00,
                "fields": [
                    {"name": "Title", "value": title, "inline": False},
                    {"name": "Author", "value": author, "inline": True},
                    {"name": "Published At", "value": published_at, "inline": False},
                ]
                + (
                    [
                        {
                            "name": "🔗 Read Article",
                            "value": f"[View on College Counter]({article_url})",
                            "inline": False,
                        }
                    ]
                    if article_url
                    else []
                ),
                "image": {"url": image_url} if image_url else None,
                "timestamp": published_at,
                "footer": {"text": "College Counter CMS"},
            }

            # Discord expects {"embeds": [embed]}
            requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})

            return Response({"status": "ok"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
