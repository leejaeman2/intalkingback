from ninja import Schema

class NoticeOutputSchema(Schema):
  id: int
  author: str
  type: str
  title: str
  content: str
  created_at: str
