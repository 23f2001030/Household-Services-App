from app import create_app, db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        from app.models import User
        from app import bcrypt
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin = User(
                email='admin@example.com',
                password=hashed_password,
                user_type='admin',
                fullname='Admin User'
            )
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)