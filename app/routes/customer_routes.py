from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from datetime import datetime, timedelta

from sqlalchemy import func
from app.models import Service, ServiceCategory, ServiceRequest, User
from app import db
from .auth_routes import redirect_to_dashboard

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

# Customer Dashboard Route
@customer_bp.route('/dashboard')
@login_required
def customer_dashboard():
    if current_user.user_type != 'customer':
        flash('Access denied.', 'danger')
        return redirect_to_dashboard()

    # Fetch service categories
    service_categories = ServiceCategory.query.all()

    # Fetch service requests for the current customer
    service_requests = ServiceRequest.query.filter_by(customer_id=current_user.id).all()

    return render_template(
        'customer/dashboard.html',
        categories=service_categories,
        service_requests=service_requests
    )


# Services in a Category
@customer_bp.route('/category/<int:category_id>')
@login_required
def services_in_category(category_id):
    if current_user.user_type != 'customer':
        flash('Access denied.', 'danger')
        return redirect_to_dashboard()

    # Get the category and its services
    category = ServiceCategory.query.get_or_404(category_id)
    services = Service.query.filter_by(category_id=category_id).all()

    return render_template('customer/services_in_category.html', category=category, services=services)


# Book a Service
@customer_bp.route('/book/<int:service_id>', methods=['POST'])
@login_required
def book_service(service_id):
    if current_user.user_type != 'customer':
        flash('Access denied.', 'danger')
        return redirect_to_dashboard()

    service = Service.query.get_or_404(service_id)

    # Create a new service request
    service_request = ServiceRequest(
        customer_id=current_user.id,
        service_id=service.id,
        status='requested',
        created_at=datetime.utcnow()
    )
    db.session.add(service_request)
    db.session.commit()

    # Notify professionals in the service's category
    professionals = User.query.filter_by(
        user_type='professional',
        service_category_id=service.category_id,
        status='approved'
    ).all()

    # Here you can implement a notification system to inform professionals

    flash(f'Service "{service.name}" has been requested successfully!', 'success')
    return redirect(url_for('customer.customer_dashboard'))


# Close a Service Request
@customer_bp.route('/close_request/<int:request_id>', methods=['POST'])
@login_required
def close_request(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)

    # Check if the customer is the one who made the request
    if service_request.customer_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('customer.customer_dashboard'))

    # Allow closing for both 'accepted' and 'in_progress' statuses
    if service_request.status not in ['accepted', 'in_progress']:
        flash('Cannot close a request that is not in progress or accepted.', 'danger')
        return redirect(url_for('customer.customer_dashboard'))

    # Mark the service as completed
    service_request.status = 'completed'
    db.session.commit()

    # Redirect to feedback form
    flash('Service marked as completed. Please provide feedback.', 'success')
    return redirect(url_for('customer.feedback_form', request_id=request_id))




# Feedback Form
@customer_bp.route('/feedback/<int:request_id>', methods=['GET', 'POST'])
@login_required
def feedback_form(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)

    if service_request.customer_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('customer.customer_dashboard'))

    if request.method == 'POST':
        # Save feedback
        service_request.rating = request.form.get('rating', type=int)
        service_request.review = request.form.get('review', type=str)
        service_request.status = 'closed'
        db.session.commit()

        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('customer.customer_dashboard'))

    # Render feedback form
    return render_template('customer/feedback_form.html', service_request=service_request)

@customer_bp.route('/search', methods=['GET'])
def search():
    search_type = request.args.get('search_type')
    search_query = request.args.get('search_query')

    results = []

    if search_type == 'service_name':
        # Query services by name
        services = Service.query.filter(Service.name.ilike(f'%{search_query}%')).all()

        # Iterate through each service and get the unique professionals for that service
        for service in services:
            professionals = set()  # To store unique professionals for the service
            for service_request in service.requests:
                professional = service_request.professional
                if professional and professional not in professionals:
                    professionals.add(professional)
                    # Check if the professional has valid data (experience, address)
                    if professional.address and professional.experience:
                        results.append({
                            'service': service,
                            'professional': professional
                        })

    elif search_type == 'pin_code':
        # Query users by pin code and join with service request and services
        users = User.query.filter(User.pin_code.like(f'%{search_query}%')) \
            .join(ServiceRequest, User.id == ServiceRequest.professional_id) \
            .join(Service, ServiceRequest.service_id == Service.id).all()

        # Collect unique professional-service pairs
        for user in users:
            for service_request in user.service_requests_professional:
                professional = user
                if professional.address and professional.experience:
                    if {
                        'service': service_request.service,
                        'professional': professional
                    } not in results:
                        results.append({
                            'service': service_request.service,
                            'professional': professional
                        })

    return render_template('customer/search.html', results=results)



@customer_bp.route('/summary', endpoint='customer_summary')
def summary():
    customer_id = current_user.id

    # Total Services
    total_services_query = db.session.query(ServiceRequest).filter(
        ServiceRequest.customer_id == customer_id,
        ServiceRequest.status.in_(['accepted', 'in_progress', 'completed', 'closed'])
    )
    total_services = total_services_query.count()

    # Total Expenditure
    total_expenditure = db.session.query(func.sum(Service.base_price)).join(ServiceRequest).filter(
        ServiceRequest.customer_id == customer_id,
        ServiceRequest.status.in_(['accepted', 'in_progress', 'completed', 'closed'])
    ).scalar() or 0

    # Average Rating
    average_rating = db.session.query(func.avg(ServiceRequest.rating)).filter(
        ServiceRequest.customer_id == customer_id,
        ServiceRequest.status.in_(['completed', 'closed']),
        ServiceRequest.rating.isnot(None)
    ).scalar() or 0

    # Pie Chart: Service Status
    service_status_distribution = db.session.query(
        ServiceRequest.status,
        func.count(ServiceRequest.id)
    ).filter(
        ServiceRequest.customer_id == customer_id
    ).group_by(ServiceRequest.status).all()

    # Line Chart: Daily Services (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_services = db.session.query(
        func.date(ServiceRequest.created_at).label('date'),
        func.count(ServiceRequest.id)
    ).filter(
        ServiceRequest.customer_id == customer_id,
        ServiceRequest.created_at >= thirty_days_ago
    ).group_by(func.date(ServiceRequest.created_at)).all()

    # Bar Chart: Average Ratings of Professionals
    professional_ratings = db.session.query(
        User.fullname,
        func.avg(ServiceRequest.rating)
    ).join(ServiceRequest, ServiceRequest.professional_id == User.id).filter(
        ServiceRequest.customer_id == customer_id,
        ServiceRequest.rating.isnot(None)
    ).group_by(User.fullname).all()

    # Convert data to renderable format
    service_status_data = {
        status: count for status, count in service_status_distribution
    }
    daily_service_data = {
        str(date): count for date, count in daily_services
    }
    professional_ratings_data = {
        name: round(avg_rating, 2) for name, avg_rating in professional_ratings
    }

    # Data for template
    data = {
        'total_services': total_services,
        'total_expenditure': total_expenditure,
        'average_rating': round(average_rating, 2),
        'service_status': service_status_data,
        'daily_services': daily_service_data,
        'professional_ratings': professional_ratings_data
    }
    
    status_labels = list(service_status_data.keys())
    status_counts = list(service_status_data.values())

    return render_template('customer/summary.html', data=data, status_labels=status_labels, status_counts=status_counts)
