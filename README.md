# Employee Training & Certification Management

A comprehensive system for managing employee training, certifications, and compliance with automated expiry tracking and smart notifications.

## 🔍 Overview
An HR-focused solution that helps organizations:  
- Manage training courses and sessions  
- Track employee enrollments and completion  
- Automatically issue certificates  
- Monitor expiry and compliance deadlines  

Includes a dynamic dashboard built with modern Odoo web technologies.

## ⚙️ Key Features

### Core
- Training & Session Management  
- Enrollment Workflow (Draft → Confirmed → Attended)  
- Automatic Certificate Generation (PDF format)  
- Expiry Tracking & Notification System  
- Role-based Security (Employee / HR Manager)  

### Advanced
- Interactive Dashboard with real-time statistics  
- Employee Portal for viewing enrollments and certificates  
- Cron-based compliance checks  
- Seat capacity and validation rules  

## 📊 Dashboard Highlights
- Real-time stats (sessions, enrollments, expiring certificates)  
- Enrollment trends visualization  
- Upcoming sessions overview  
- Quick enrollment modal  

## 🧩 Module Structure
```
employee_training/
├── models/
│   ├── training_course.py
│   ├── training_session.py
│   ├── training_enrollment.py
│   └── training_certificate.py
├── views/
│   ├── dashboard, portal & report XMLs
├── controllers/
│   └── portal.py
├── security/
│   ├── ir.model.access.csv
│   └── training_security.xml
├── data/
│   ├── mail_template.xml
│   └── training_cron.xml
└── static/src/components/
    ├── training_dashboard.js
    ├── training_dashboard.xml
    └── training_dashboard.scss
```

## 🧠 Data Model
```
training.course → training.session → training.enrollment → training.certificate
hr.employee → training.enrollment
```

## 🔐 Security
- **Training User:** Read-only access  
- **Training Manager:** Full access  
- Portal users: Limited to personal records  

## 🧪 Testing
- Enrollment workflow validation  
- Certificate generation logic  
- Expiry date computation  
- Access control and record rules  

## 🧭 Compatibility
- **Compatible with Odoo version 18.0**

## 🚀 Roadmap
- Skill matrix integration  
- Training budget tracking  
- Advanced analytics dashboard  
- LMS and multi-company support  

---

**Developed using Odoo best practices with a focus on automation, usability, and compliance.**