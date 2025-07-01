from dataclasses import dataclass, field
from typing import List


@dataclass
class Comment:

    id: int
    post_id: int
    user: str
    content: str
    created_at: str


@dataclass
class Post:

    id: int
    user: str
    content: str
    image_url: str
    created_at: str
    likes: int
    comments: List[Comment] = field(default_factory=list)
