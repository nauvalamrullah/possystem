# models.py
from database import db

class FundingRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    amount = db.Column(db.Float)
    status = db.Column(db.String(20))
    purpose = db.Column(db.String(255))
