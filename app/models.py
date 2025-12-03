from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'customer', 'professional', 'admin'
    fullname = db.Column(db.String(100))
    address = db.Column(db.Text)
    pin_code = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Additional fields for professionals
    service_category_id = db.Column(db.Integer, db.ForeignKey('service_category.id'))  # New field
    service_name = db.Column(db.String(100))  # Optional, if needed for specific service within category
    experience = db.Column(db.Integer)
    document_path = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'

    # Relationships
    service_requests_customer = db.relationship('ServiceRequest', 
                                              backref='customer',
                                              foreign_keys='ServiceRequest.customer_id',
                                              lazy=True)
    service_requests_professional = db.relationship('ServiceRequest', 
                                                  backref='professional',
                                                  foreign_keys='ServiceRequest.professional_id',
                                                  lazy=True)

    service_category = db.relationship('ServiceCategory', backref='professionals')

    @property
    def is_admin(self):
        return self.user_type == 'admin'

    @property
    def is_professional(self):
        return self.user_type == 'professional'

    @property
    def is_customer(self):
        return self.user_type == 'customer'


class ServiceCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    # Relationship with services
    services = db.relationship('Service', backref='category', lazy=True)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    
    # Foreign key for service category
    category_id = db.Column(db.Integer, db.ForeignKey('service_category.id'), nullable=False)
    
    # Relationship with service requests
    requests = db.relationship('ServiceRequest', backref='service', lazy=True)

class RejectedRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('service_request.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    service_request = db.relationship('ServiceRequest', backref='rejected_requests')
    professional = db.relationship('User', backref='rejected_services')

class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Accepted professional
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    status = db.Column(db.String(20), default='requested')  # requested, accepted, closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    rating = db.Column(db.Integer)
    review = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Many-to-many relationship for rejected professionals
    rejected_professionals = db.relationship(
        'User', 
        secondary='rejected_requests_association',
        backref='rejected_service_requests'
    )

# Association table for many-to-many relationship
rejected_requests_association = db.Table(
    'rejected_requests_association',
    db.Column('service_request_id', db.Integer, db.ForeignKey('service_request.id'), primary_key=True),
    db.Column('professional_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)