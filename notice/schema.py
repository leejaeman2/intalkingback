from ninja import Schema

class NoticeOutputSchema(Schema):
  id: int
  author: str
  type: str
  title: str
  content: str
  event_date: str | None = None
  created_at: str
