from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager

playlist_tracks=db.Table('playlist_tracks',
 db.Column('playlist_id',db.Integer,db.ForeignKey('playlist.id'),primary_key=True),
 db.Column('track_id',db.Integer,db.ForeignKey('track.id'),primary_key=True))
class User(UserMixin,db.Model):
 id=db.Column(db.Integer,primary_key=True); username=db.Column(db.String(50),unique=True,nullable=False,index=True)
 password_hash=db.Column(db.String(255),nullable=False); is_admin=db.Column(db.Boolean,default=False); created_at=db.Column(db.DateTime,default=datetime.utcnow)
 def set_password(self,p): self.password_hash=generate_password_hash(p)
 def check_password(self,p): return check_password_hash(self.password_hash,p)
class Track(db.Model):
 id=db.Column(db.Integer,primary_key=True); title=db.Column(db.String(300),nullable=False); artist=db.Column(db.String(200),default='Unknown Artist')
 album=db.Column(db.String(200),default='Imported'); filename=db.Column(db.String(500),nullable=False,unique=True); artwork=db.Column(db.String(500))
 source_url=db.Column(db.Text); duration=db.Column(db.Integer,default=0); added_by=db.Column(db.Integer,db.ForeignKey('user.id'))
 created_at=db.Column(db.DateTime,default=datetime.utcnow); plays=db.Column(db.Integer,default=0)
class Playlist(db.Model):
 id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(100),nullable=False); owner_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
 tracks=db.relationship('Track',secondary=playlist_tracks,lazy='subquery',backref=db.backref('playlists',lazy=True))
@login_manager.user_loader
def load_user(uid): return db.session.get(User,int(uid))
