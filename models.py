# models.py
from databases import db
from app import db
from pytz import timezone
from datetime import datetime


class BandwidthStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    eth_type = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(255), nullable=False)
    speed = db.Column(db.BigInteger, nullable=False)
    speed_send = db.Column(db.BigInteger, nullable=False)
    speed_recv = db.Column(db.BigInteger, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone('Asia/Jakarta')))
    
class System(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cpu_idle = db.Column(db.String(255), nullable=False)
    ram_total = db.Column(db.BigInteger, nullable=False)
    ram_free = db.Column(db.BigInteger, nullable=False)
    conntrack = db.Column(db.BigInteger, nullable=False)
    userol = db.Column(db.BigInteger, nullable=False)
    userhs = db.Column(db.BigInteger, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone('Asia/Jakarta')))

class LoadBalance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interface = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(255), nullable=False)
    tracking = db.Column(db.String(255), nullable=False)
    percentage = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone('Asia/Jakarta')))

class HS_user(db.Model):
    username = db.Column(db.String(255), primary_key=True)
    password = db.Column(db.String(255), nullable=False)
    tipe = db.Column(db.String(255), nullable=True)
    qoutaused= db.Column(db.BigInteger, nullable=True)
    lastlogin= db.Column(db.DateTime, nullable=True)
    uptime= db.Column(db.BigInteger, nullable=True)

class HS_profile(db.Model):
    tipe = db.Column(db.String(255), primary_key=True)
    mode = db.Column(db.String(255), nullable=False)
    session= db.Column(db.BigInteger, nullable=False)
    down_rate = db.Column(db.BigInteger, nullable=False)
    up_rate = db.Column(db.BigInteger, nullable=False)
    down_qouta= db.Column(db.BigInteger, nullable=False)
    up_qouta= db.Column(db.BigInteger, nullable=False)    

class DNS_access(db.Model):
    url = db.Column(db.String(255), primary_key=True)
    num_access = db.Column(db.BigInteger, nullable=False)
    mode = db.Column(db.String(255), nullable=True)