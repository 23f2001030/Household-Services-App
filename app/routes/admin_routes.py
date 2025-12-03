# Define blueprints for modular routes - chatgpt se uthaya
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app import db
from app.models import Service, ServiceCategory, ServiceRequest, User
from .auth_routes import redirect_to_dashboard
from sqlalchemy import and_, or_
from flask import jsonify


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin Dashboard Route
@admin_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.user_type != 'admin':
        flash('Access denied.', 'danger')
        return redirect_to_dashboard()

    # Fetch all professionals (approved, rejected, and pending)
    professionals = User.query.filter_by(user_type='professional').all()
    pending_professionals = User.query.filter_by(user_type='professional', status='pending').all()

    # Fetch all services
    services = Service.query.join(ServiceCategory).all()

    # Fetch all service requests
    service_requests = ServiceRequest.query.join(Service).join(User, ServiceRequest.professional_id == User.id, isouter=True).all()

    # Count service requests by their status (accepted and closed are used instead of in_progress and completed)
    status_counts = {
        'pending': ServiceRequest.query.filter_by(status='pending').count(),
        'accepted': ServiceRequest.query.filter_by(status='accepted').count(),
        'closed': ServiceRequest.query.filter_by(status='closed').count(),
    }

    # Handle POST request for changing status
    if request.method == 'POST':
        service_request_id = request.form.get('service_request_id')
        new_status = request.form.get('status')

        if service_request_id and new_status:
            service_request = ServiceRequest.query.get(service_request_id)
            if service_request:
                service_request.status = new_status
                db.session.commit()
                flash(f"Service request status updated to {new_status}.", 'success')

    return render_template(
        'admin/dashboard.html',
        users=professionals,
        pending_users=pending_professionals,
        services=services,
        service_requests=service_requests,
        status_counts=status_counts
    )




# Admin Search Route
@admin_bp.route('/search', methods=['GET', 'POST'])
@login_required
def admin_search():
    if current_user.user_type != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    # Retrieve search parameters
    search_query = request.args.get('query', '').strip()
    search_type = request.args.get('type', 'service')  # Default to 'service'
    results = []

    # Search logic based on selected type
    if search_query:
        if search_type == 'service':
            results = Service.query.filter(
                or_(
                    Service.name.ilike(f"%{search_query}%"),
                    Service.description.ilike(f"%{search_query}%")
                )
            ).all()
        elif search_type == 'customer':
            results = User.query.filter(
                and_(
                    User.user_type == 'customer',
                    or_(
                        User.fullname.ilike(f"%{search_query}%"),
                        User.email.ilike(f"%{search_query}%")
                    )
                )
            ).all()
        elif search_type == 'professional':
            results = User.query.filter(
                and_(
                    User.user_type == 'professional',
                    or_(
                        User.fullname.ilike(f"%{search_query}%"),
                        User.email.ilike(f"%{search_query}%")
                    )
                )
            ).all()
        elif search_type == 'service_request':
            results = ServiceRequest.query.join(Service).join(User, ServiceRequest.professional_id == User.id, isouter=True).filter(
                or_(
                    ServiceRequest.status.ilike(f"%{search_query}%"),
                    Service.name.ilike(f"%{search_query}%"),
                    User.fullname.ilike(f"%{search_query}%")
                )
            ).all()

    return render_template(
        'admin/search.html',
        query=search_query,
        search_type=search_type,
        results=results
    )



# Admin Summary Route
@admin_bp.route('/summary')
@login_required
def admin_summary():
    if current_user.user_type != 'admin':
        flash('Access denied.', 'danger')
        return redirect_to_dashboard()

    # Fetch overall statistics
    total_customers = User.query.filter_by(user_type='customer').count()
    total_professionals = User.query.filter_by(user_type='professional').count()
    total_services = Service.query.count()
    total_service_requests = ServiceRequest.query.count()

    # Fetch service requests by status (for pie chart)
    status_data = (
        db.session.query(ServiceRequest.status, db.func.count(ServiceRequest.id))
        .group_by(ServiceRequest.status)
        .all()
    )
    status_data = {status: count for status, count in status_data}

    # Fetch requests by service category (for bar chart)
    service_category_data = (
        db.session.query(ServiceCategory.name, db.func.count(ServiceRequest.id))
        .join(Service, ServiceCategory.id == Service.category_id)
        .join(ServiceRequest, Service.id == ServiceRequest.service_id)
        .group_by(ServiceCategory.name)
        .all()
    )
    service_category_data = {category: count for category, count in service_category_data}

    return render_template(
        'admin/summary.html',
        total_customers=total_customers,
        total_professionals=total_professionals,
        total_services=total_services,
        total_service_requests=total_service_requests,
        status_data=status_data,
        service_data=service_category_data
    )





@admin_bp.route('/approve/<int:user_id>', methods=['POST'])
@login_required
def approve_professional(user_id):
    if current_user.user_type != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    user = User.query.get_or_404(user_id)
    if user.user_type == 'professional' and user.status != 'approved':
        user.status = 'approved'
        db.session.commit()
        flash(f"Professional {user.fullname} approved successfully!", 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/reject/<int:user_id>', methods=['POST'])
@login_required
def reject_professional(user_id):
    if current_user.user_type != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    user = User.query.get_or_404(user_id)
    if user.user_type == 'professional' and user.status != 'rejected':
        user.status = 'rejected'
        db.session.commit()
        flash(f"Professional {user.fullname} rejected successfully!", 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/create-service', methods=['GET', 'POST'])
def create_service():
    if request.method == 'POST':
        service_name = request.form['service_name']
        description = request.form['description']
        base_price = request.form['base_price']
        category_id = request.form['category_id']
        
        # Create a new Service instance
        new_service = Service(
            name=service_name,
            description=description,
            base_price=base_price,
            category_id=category_id
        )
        
        # Add the service to the database
        db.session.add(new_service)
        db.session.commit()

        flash('New service created successfully!', 'success')
        # Redirect to the admin dashboard after creating the service
        return redirect(url_for('admin.admin_dashboard'))

    # For GET request, fetch all categories from the database
    categories = ServiceCategory.query.all()

    # Render the form with the list of categories
    return render_template('admin/create_service.html', categories=categories)


@admin_bp.route('/edit-service/<int:service_id>', methods=['GET', 'POST'])
@login_required
def edit_service(service_id):
    if current_user.user_type != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    service = Service.query.get_or_404(service_id)

    if request.method == 'POST':
        service.name = request.form['service_name']
        service.description = request.form['description']
        service.base_price = request.form['base_price']
        db.session.commit()

        flash(f'Service "{service.name}" updated successfully!', 'success')
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('admin/edit_service.html', service=service)

@admin_bp.route('/delete-service/<int:service_id>', methods=['POST'])
@login_required
def delete_service(service_id):
    if current_user.user_type != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    service = Service.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()

    flash(f'Service "{service.name}" deleted successfully!', 'success')
    return redirect(url_for('admin.admin_dashboard'))