import os
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename
from app.models import ServiceCategory, User
from app import db
from app import bcrypt


auth = Blueprint('auth', __name__)

@auth.route('/', methods=['GET', 'POST'])
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect_to_dashboard()

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Query the user by email
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            # Check user type and status for professionals
            if user.user_type == 'professional':
                if user.status == 'pending':
                    flash('Your account is waiting for admin approval.', 'warning')
                    return redirect(url_for('auth.login'))
                elif user.status == 'rejected':
                    flash('Your profile was rejected by the admin.', 'danger')
                    return redirect(url_for('auth.login'))

            # If user is approved or not a professional, allow login
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect_to_dashboard()

        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')

    return render_template('login.html')

def redirect_to_dashboard():
    if current_user.user_type == 'admin':
        return redirect(url_for('admin.admin_dashboard'))
    elif current_user.user_type == 'customer':
        return redirect(url_for('customer.customer_dashboard'))
    else:
        return redirect(url_for('professional.professional_dashboard'))

@auth.route('/register/customer', methods=['GET', 'POST'])
def customer_signup():
    if current_user.is_authenticated:
        return redirect_to_dashboard()
    
    if request.method == 'POST':
        hashed_pw = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        user = User(
            email=request.form['email'],
            password=hashed_pw,
            user_type='customer',
            fullname=request.form['fullname'],
            address=request.form['address'],
            pin_code=request.form['pin_code']
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('customer_signup.html')

@auth.route('/register/professional', methods=['GET', 'POST'])
def professional_signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))  # Redirect to a dashboard or the relevant page
    
    # Get all service categories for the dropdown
    service_categories = ServiceCategory.query.all()

    if request.method == 'POST':
        # Handle file upload
        file = request.files.get('document')
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
        else:
            file_path = None

        # Hash the password
        hashed_pw = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        # Get the form data
        user = User(
            email=request.form['email'],
            password=hashed_pw,
            user_type='professional',
            fullname=request.form['fullname'],
            service_category_id=request.form['service_category'],  # Use the category ID
            experience=request.form['experience'],
            address=request.form['address'],
            pin_code=request.form['pin_code'],
            document_path=file_path
        )

        # Add the new user to the database
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))  # Redirect to the login page

    # Render the registration form, passing the service categories for the dropdown
    return render_template('professional_signup.html', service_categories=service_categories)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))