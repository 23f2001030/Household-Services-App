# Household-Services-App

-   **NAME:** AMAN KUMAR
    
-   **ROLL NO:** 23F2001030
    
-   **MAIL:** 23f2001030@ds.study.iitm.ac.in
    

----------
[Drive Link to Presentation Video](https://drive.google.com/file/d/1xkOoM-GXsjm6xYwvwn21P0S6HZ4ZL6eJ/view)
----------

Project Statement

The "A to Z Household Services Application" is a multi-user platform designed to provide a comprehensive home servicing solution. It connects administrators, service professionals, and customers for streamlined management and service execution.

Problem Statement

The challenge was to create a platform where:

1.  Customers could book and manage household services.
    
2.  Service professionals could manage service requests efficiently.
    
3.  Admins could oversee all platform activities, including user management and service monitoring14.
    

Approach 

1.  Defined the architecture for multi-user roles: Admin, Service Professional, and Customer.
    
2.  Designed a user-friendly interface using Jinja2 Templates and Bootstrap.
    
3.  Created a database structure using SQLite to ensure efficient data handling.
    
4.  Implemented server-side logic using Flask for backend processing.
    

----------

Frameworks and Libraries Used 

-   **Flask:** Application framework.
    
-   **Jinja2 Templates:** For dynamic HTML generation.
    
-   **Bootstrap:** For responsive and visually appealing front-end designs.
    
-   **SQLite:** Lightweight database for efficient local storage.
    
-   **Flask-Login, Flask-Bcrypt, Flask-Migrate:** For user authentication, password encryption, and database migrations.
    

----------

Database

The ER Diagram illustrates the relationships between various tables in the system:

1.  **User Table:** Stores details of Admins, Customers, and Professionals.
    
    -   **Relationships:** Links to `serviceRequest` as both Customer and Professional.
        
2.  **ServiceCategory Table:** Categorizes services.
    
    -   **Relationships:** Links to `service` table.
        
3.  **Service Table:** Stores service-specific details (e.g., name, price).
    
    -   **Relationships:** Links to `serviceRequest`.
        
4.  **ServiceRequest Table:** Tracks requests from creation to completion.
    
    -   **Relationships:** Links to `user` (as both customer and professional) and `Service`.
        

Entities and Relations 

-   **User** (id, email, password, user_type, ...) one-to-many **ServiceRequest**.
    
-   **ServiceCategory** (id, name) one-to-many → **Service**.
    
-   **Service** (id, name, category_id, ...) one-to-many **ServiceRequest**.
    

_(Note: The report contains a visual Diagram at this stage illustrating the connections between User, ServiceCategory, Service, ServiceRequest, and RejectedRequest tables)_ 

----------

API Resource Endpoints 

The system employs internal endpoints to manage interactions. Key endpoints include:

1. Authentication: 

-   `Login` and `/register` (POST): For user login and registration.
    

2. Admin Operations: 

-   `/admin/dashboard`: View overall activities.
    
-   `/admin/create-service`: Add new services.
    
-   `/admin/search`: Search users, services, and requests.
    

3. Customer Operations: 

-   `/customer/book/<service id>`: Book a service.
    
-   `/customer/close_request/<request id>`: Mark service as completed.
    

4. Professional Operations: 

-   `/professional/accept_request/<request id>`: Accept service requests.
    
-   `/professional/summary`: View service summary and earnings.
