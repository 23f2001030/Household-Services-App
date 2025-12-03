# Define blueprints for modular routes
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import and_
from app.models import RejectedRequest, Service, ServiceCategory, ServiceRequest, User
from app import db

professional_bp = Blueprint('professional', __name__, url_prefix='/professional')

# Professional Dashboard Route
@professional_bp.route('/dashboard')
@login_required
def professional_dashboard():
    if current_user.user_type != 'professional':
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.login'))

    # Subquery for rejected requests by this professional
    rejected_subquery = db.session.query(RejectedRequest.request_id).filter(
        RejectedRequest.professional_id == current_user.id
    ).subquery()

    # Fetch available service requests (same category, not rejected or accepted)
    available_requests = ServiceRequest.query.join(Service).filter(
        and_(
            Service.category_id == current_user.service_category_id,
            ServiceRequest.status == 'requested',
            ServiceRequest.id.not_in(rejected_subquery),
            ServiceRequest.professional_id == None
        )
    ).all()

    # Fetch accepted or in-progress requests for this professional
    accepted_requests = ServiceRequest.query.filter(
        ServiceRequest.professional_id == current_user.id,
        ServiceRequest.status.in_(['accepted', 'in_progress'])
    ).all()

    # Fetch closed or completed services for this professional
    closed_services = ServiceRequest.query.filter(
        ServiceRequest.professional_id == current_user.id,
        ServiceRequest.status.in_(['completed', 'closed'])
    ).all()

    # Fetch rejected requests for this professional
    rejected_requests = ServiceRequest.query.join(RejectedRequest).filter(
        RejectedRequest.professional_id == current_user.id
    ).all()

    return render_template(
        'professional/dashboard.html',
        available_requests=available_requests,
        accepted_requests=accepted_requests,
        closed_services=closed_services,
        rejected_requests=rejected_requests
    )



# Accept Request Route
@professional_bp.route('/accept_request/<int:request_id>', methods=['POST'])
@login_required
def accept_request(request_id):
    if current_user.user_type != 'professional':
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.login'))

    # Fetch the service request
    service_request = ServiceRequest.query.get_or_404(request_id)

    # Ensure the request is still available
    if service_request.status != 'requested' or service_request.professional_id:
        flash('This request is no longer available.', 'warning')
        return redirect(url_for('professional.professional_dashboard'))

    # Assign the request to the professional
    service_request.professional_id = current_user.id
    service_request.status = 'accepted'
    db.session.commit()

    flash('You have successfully accepted the request.', 'success')
    return redirect(url_for('professional.professional_dashboard'))


# Reject Request Route
@professional_bp.route('/reject_request/<int:request_id>', methods=['POST'])
@login_required
def reject_request(request_id):
    if current_user.user_type != 'professional':
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.login'))

    # Fetch the service request
    service_request = ServiceRequest.query.get_or_404(request_id)

    # Ensure the request is still available for rejection
    if service_request.status == 'accepted':
        flash('This request has already been accepted by another professional.', 'warning')
        return redirect(url_for('professional.professional_dashboard'))

    # Add the rejection to the RejectedRequest table
    rejection = RejectedRequest(request_id=request_id, professional_id=current_user.id)
    db.session.add(rejection)
    db.session.commit()

    flash('You have rejected the request.', 'success')
    return redirect(url_for('professional.professional_dashboard'))

from flask import request

@professional_bp.route('/search', methods=['GET', 'POST'])
@login_required
def professional_search():
    if current_user.user_type != 'professional':
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.login'))

    # Define search criteria and results
    search_results = []
    search_criteria = request.form.get('search_criteria', '')
    search_term = request.form.get('search_term', '')

    # Perform search based on selected criteria
    if search_criteria and search_term:
        if search_criteria == 'date':
            # Search by service request date (including all requests of this professional)
            search_results = ServiceRequest.query.filter(
                ServiceRequest.created_at.like(f'%{search_term}%'),
                (ServiceRequest.professional_id == current_user.id) | 
                (ServiceRequest.id.in_(db.session.query(RejectedRequest.request_id).filter(RejectedRequest.professional_id == current_user.id)))
            ).all()
        elif search_criteria == 'address':
            # Search by customer address (specifying the 'customer_id' foreign key)
            search_results = ServiceRequest.query.join(User, ServiceRequest.customer_id == User.id).filter(
                User.address.like(f'%{search_term}%'),
                ServiceRequest.professional_id == current_user.id
            ).all()
        elif search_criteria == 'pin_code':
            # Search by customer pin code (specifying the 'customer_id' foreign key)
            search_results = ServiceRequest.query.join(User, ServiceRequest.customer_id == User.id).filter(
                User.pin_code.like(f'%{search_term}%'),
                ServiceRequest.professional_id == current_user.id
            ).all()

    return render_template('professional/search.html', search_results=search_results)



from sqlalchemy import func

@professional_bp.route('/summary', methods=['GET'])
@login_required
def professional_summary():
    if not current_user.is_professional:
        return "Unauthorized", 403

    # Total services completed (completed or closed)
    total_services = ServiceRequest.query.filter(
        ServiceRequest.professional_id == current_user.id,
        ServiceRequest.status.in_(['completed', 'closed'])
    ).count()

    # Daily earnings (only completed or closed services)
    earnings_data = db.session.query(
        db.func.date(ServiceRequest.completed_at).label('day'),  # Group by day
        db.func.sum(Service.base_price).label('total_earnings')
    ).join(Service).filter(
        ServiceRequest.professional_id == current_user.id,
        ServiceRequest.status.in_(['completed', 'closed'])
    ).group_by('day').order_by('day').all()

    earnings_labels = [row.day for row in earnings_data]
    earnings_values = [row.total_earnings for row in earnings_data]

    # Ratings distribution
    rating_data = db.session.query(
        ServiceRequest.rating, db.func.count(ServiceRequest.id)
    ).filter(
        ServiceRequest.professional_id == current_user.id,
        ServiceRequest.rating.isnot(None)
    ).group_by(ServiceRequest.rating).all()

    rating_labels = [str(row.rating) for row in rating_data]
    rating_counts = [row[1] for row in rating_data]

    # Service requests per service (all statuses, by category)
    service_data = db.session.query(
        Service.name, db.func.count(ServiceRequest.id)
    ).join(ServiceRequest).filter(
        Service.category_id == current_user.service_category_id
    ).group_by(Service.id).all()

    service_labels = [row.name for row in service_data]
    service_counts = [row[1] for row in service_data]

    return render_template(
        'professional/summary.html',
        total_services=total_services,
        earnings_labels=earnings_labels,
        earnings_values=earnings_values,
        rating_labels=rating_labels,
        rating_counts=rating_counts,
        service_labels=service_labels,
        service_counts=service_counts
    )
