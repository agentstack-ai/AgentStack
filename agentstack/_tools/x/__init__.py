from typing import Optional, Union
import os
import tweepy


CLIENT_ID = os.getenv('X_CLIENT_ID')
CLIENT_SECRET = os.getenv('X_CLIENT_SECRET')
ACCESS_TOKEN = os.getenv('X_ACCESS_TOKEN')
CALLBACK_URL = os.getenv('X_CALLBACK_URL', "https://localhost:7000")

SCOPES_READ = [
    'users.read',
    'tweet.read',
    #'follows.read',
    #'like.read',
]
SCOPES_WRITE = [
    'tweet.write',
    #'follows.write',
    #'like.write',
]
SCOPES = SCOPES_READ + SCOPES_WRITE

_client: tweepy.Client = None
_current_user_id: Optional[str] = None  # cache the current user's ID for re-use


def get_client() -> tweepy.Client:
    """
    Get the client.
    """
    global _client, ACCESS_TOKEN
    if _client is not None:
        return _client
    
    # TODO refresh token
    if not ACCESS_TOKEN:
        oauth_handler = tweepy.OAuth2UserHandler(
            client_id=CLIENT_ID, 
            client_secret=CLIENT_SECRET, 
            scope=SCOPES, 
            redirect_uri=CALLBACK_URL,)
        auth_url = oauth_handler.get_authorization_url()
        print("Authorize on X to use the API")
        print(f"Open this URL in your browser: {auth_url}")
        verifier = input(f"Enter the PIN provided: ")
        response = oauth_handler.fetch_token(verifier)
        ACCESS_TOKEN = response['access_token']

    _client = tweepy.Client(ACCESS_TOKEN)
    return _client


def get_current_user_id() -> str:
    """
    Get the current user's ID.
    """
    global _current_user_id
    if not _current_user_id:
        _current_user_id = str(get_my_profile().get('id'))
    return _current_user_id


def get_my_profile() -> dict:
    """
    Get the user's profile.
    """
    # returns:
    # {
    #     "id": "2244994945",
    #     "name": "TwitterDev",
    #     "username": "Twitter Dev"
    # }
    client = get_client()
    kwargs = {
        'user_fields': [
            'id', 
            'name', 
            'username', 
        ],
    }
    return client.get_me(**kwargs).get('data')


def get_timeline(max_results: int = 25, since_id: Optional[int] = None, until_id: Optional[int] = None) -> list[dict]:
    """
    Get the user's home timeline.
    
    `max_results` Specifies the number of Tweets to try and retrieve, up to a maximum of 100 per 
    distinct request. By default, 25 results are returned if this parameter is not supplied. 
    
    `since_id` Returns results with a Tweet ID greater than (that is, more recent than) the 
    specified 'since' Tweet ID.
    
    `until_id` Returns results with a Tweet ID less than (that is, older than) the specified 
    'until' Tweet ID. 
    """
    client = get_client()
    kwargs = {
        'max_results': max_results,
        'since_id': since_id,
        'until_id': until_id,
    }
    return client.get_home_timeline(**kwargs).get('data')


def get_user_by_username(username: str) -> dict:
    """
    Get a user by username.
    """
    # returns:
    # {
    #     "id": "2244994945",
    #     "name": "Twitter Dev",
    #     "username": "TwitterDev",
    #     "url": "https://t.co/FGlZ7YpHd1",
    #     "description": "Your official source for Twitter Platform news, updates & events. Need technical help? Visit https://t.co/mGHnxZU8c1 ⌨️ #TapIntoTwitter",
    #     "location": "Internet",
    #     "most_recent_tweet_id": "1448612029053100550",
    #     "pinned_tweet_id": "1448612029053100550",
    #     "profile_image_url": "https://pbs.twimg.com/profile_images/1449394334024927745/0bKs3k3X_normal
    # }
    client = get_client()
    kwargs = {
        'username': username,
        'user_fields': [
            'id', 
            'name', 
            'username', 
            'url', 
            'description', 
            'location', 
            'most_recent_tweet_id',
            'pinned_tweet_id', 
            'profile_image_url', 
        ],
    }
    return client.get_user(**kwargs).get('data')


def get_tweet_by_id(tweet_id: str) -> dict:
    """
    Get a tweet by tweet ID.
    """
    # returns:
    # {
    #     "id": "1460323737035677698",
    #     "text": "Introducing a new era for the Twitter Developer Platform!",
    #      "edit_history_tweet_ids": [
    #          "1460323737035677698"
    #      ],
    #     "public_metrics": {
    #         "retweet_count": 0,
    #         "reply_count": 0,
    #         "like_count": 0,
    #         "quote_count": 0
    #     },
    #     "includes": {
    #         ...
    #     }
    # }
    client = get_client()
    kwargs = {
        'id': tweet_id, 
        'tweet_fields': [
            'id', 
            'text', 
            'public_metrics', 
        ],
        'user_fields': [
            'id', 
            'name', 
            'username', 
            'location', 
            'profile_image_url', 
            'public_metrics',
        ],
    }
    return client.get_tweet(**kwargs).get('data')


def create_tweet(text: str) -> dict:
    """
    Create a tweet.
    """
    # returns:
    # {
    #     "id": "1445880548472328192",
    #     "text": "Are you excited for the weekend?",
    # }
    client = get_client()
    kwargs = {
        'text': text,
    }
    return client.create_tweet(**kwargs).get('data')


def create_retweet(tweet_id: str) -> dict:
    """
    Retweet a tweet by tweet ID.
    """
    # returns:
    # {
    #     "retweeted": true
    # }
    client = get_client()
    return client.retweet(tweet_id).get('data')


def create_quote(tweet_id: str, text: str) -> dict:
    """
    Quote a tweet by tweet ID and add text.
    """
    # returns:
    # {
    #     "id": "1445880548472328192",
    #     "text": "Are you excited for the weekend?"
    # }
    client = get_client()
    kwargs = {
        'quote_tweet_id': tweet_id,
        'text': text,
    }
    return client.create_tweet(**kwargs).get('data')


def create_reply(tweet_id: str, text: str) -> dict:
    """
    Reply to a tweet by tweet ID.
    """
    # returns:
    # {
    #     "id": "1445880548472328192",
    #     "text": "Are you excited for the weekend?"
    # }
    client = get_client()
    kwargs = {
        'in_reply_to_tweet_id': tweet_id,
        'text': text,
    }
    return client.create_tweet(**kwargs).get('data')


def get_my_followers(max_results: int = 25, pagination_token: Optional[str] = None) -> list[dict]:
    """
    Get your followers.
    
    `max_results` Specifies the number of Tweets to try and retrieve, up to a maximum of 100 per 
    distinct request. By default, 25 results are returned if this parameter is not supplied. 
    
    `pagination_token` This parameter is used to get the next or previous page of results.
    Retrieve the token from the previous response.
    """
    # returns
    # [
    #     {
    #         "id": "6253282",
    #         "name": "Twitter API",
    #         "username": "TwitterAPI"
    #     },
    #     ...
    # ]
    client = get_client()
    kwargs = {
        'id': get_current_user_id(),
        'max_results': max_results,
        'pagination_token': pagination_token,
    }
    return client.get_users_followers(**kwargs).get('data')


def get_my_following(max_results: int = 25, pagination_token: Optional[str] = None) -> list[dict]:
    """
    Get users you are following.
    
    `max_results` Specifies the number of Tweets to try and retrieve, up to a maximum of 100 per 
    distinct request. By default, 25 results are returned if this parameter is not supplied. 
    
    `pagination_token` This parameter is used to get the next or previous page of results.
    Retrieve the token from the previous response.
    """
    # returns
    # [
    #     {
    #         "id": "6253282",
    #         "name": "Twitter API",
    #         "username": "TwitterAPI"
    #     },
    #     ...
    # ]
    client = get_client()
    kwargs = {
        'id': get_current_user_id(),
        'max_results': max_results,
        'pagination_token': pagination_token,
    }
    return client.get_users_following(**kwargs).get('data')


def create_follow(user_id: str) -> dict:
    """
    Follow a user by user ID.
    """
    # returns:
    # {
    #     "following": true,
    #     "pending_follow": false
    # }
    client = get_client()
    return client.follow_user(user_id).get('data')


def get_my_liked_tweets(max_results: int = 25, pagination_token: Optional[str] = None) -> list[dict]:
    """
    Get tweets you have liked.
    
    `max_results` Specifies the number of Tweets to try and retrieve, up to a maximum of 100 per 
    distinct request. By default, 25 results are returned if this parameter is not supplied. 
    
    `pagination_token` This parameter is used to get the next or previous page of results.
    Retrieve the token from the previous response.
    """
    # returns: 
    # [
    #     {
    #       "id": "1362449997430542337",
    #       "edit_history_tweet_ids": [
    #           "1362449997430542337"
    #       ],
    #       "text": "Honored to be the first developer to be featured in @TwitterDev's love fest 🥰♥️😍 https://t.co/g8TsPoZsij"
    #     },
    #     ...
    # ]
    client = get_client()
    kwargs = {
        'id': get_current_user_id(),
        'max_results': max_results,
        'pagination_token': pagination_token,
        'tweet_fields': [
            'id', 
            'text', 
            'public_metrics',
        ],
        'user_fields': [
            'id', 
            'name', 
            'username', 
            'public_metrics', 
        ],
    }
    return client.get_liked_tweets(**kwargs).get('data')


def get_tweet_likes(tweet_id: str, max_results: int = 25, pagination_token: Optional[str] = None) -> list[dict]:
    """
    Get likes on a tweet by tweet ID.
    
    `max_results` Specifies the number of Tweets to try and retrieve, up to a maximum of 100 per 
    distinct request. By default, 25 results are returned if this parameter is not supplied. 
    
    `pagination_token` This parameter is used to get the next or previous page of results.
    Retrieve the token from the previous response.
    """
    # returns:
    # [
    #     {
    #         "id": "6253282",
    #         "name": "Twitter API",
    #         "username": "TwitterAPI", 
    #         "public_metrics": {
    #             "followers_count": 1000,
    #             "following_count": 1000,
    #             "tweet_count": 1000,
    #             "listed_count": 1000
    #         }
    #     },
    #     ...
    # ]
    client = get_client()
    kwargs = {
        'id': tweet_id,
        'user_fields': [
            'id', 
            'name', 
            'username', 
            'public_metrics', 
        ],
    }
    return client.get_liking_users(**kwargs).get('data')


def create_like(tweet_id: str):
    """
    Like a tweet by tweet ID.
    """
    # returns:
    # {
    #     "liked": true
    # }
    client = get_client()
    kwargs = {
        'tweet_id': tweet_id,
    }
    return client.like(**kwargs).get('data')

