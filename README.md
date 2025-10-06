# Employee Training & Certification Management

A comprehensive Odoo 18 module for managing employee training programs, certifications, and compliance tracking with automated notifications and expiry monitoring.

## Overview

This module provides end-to-end training management functionality for organizations, enabling HR managers to schedule training sessions, track employee enrollments, issue certificates, and monitor compliance deadlines. Built using modern Odoo 18 features including OWL components for the dashboard interface.

## Features

### Core Functionality
- **Training Course Management**: Define courses with customizable duration and certification requirements
- **Session Scheduling**: Plan and organize training sessions with capacity management
- **Enrollment Tracking**: Monitor employee participation with workflow states (Draft → Confirmed → Attended → Cancelled)
- **Certificate Issuance**: Automatic certificate generation upon course completion
- **Expiry Monitoring**: Track certificate validity with configurable 2-year expiry periods
- **Automated Notifications**: 30-day advance warning for expiring certificates via email and activity notifications

### Advanced Features
- **Interactive Dashboard**: Real-time OWL-based dashboard with charts and statistics
- **Portal Access**: Employee self-service portal for viewing enrollments and downloading certificates
- **PDF Certificates**: Professional, branded certificate PDFs with company logo
- **Compliance Tracking**: Automated cron jobs for monitoring certification compliance
- **Capacity Management**: Real-time seat availability tracking with automatic validation
- **Security & Access Control**: Role-based permissions (Employee vs HR Manager access)

### Dashboard Components
- Statistics cards showing active sessions, monthly enrollments, expiring certificates, and completion rates
- Interactive Chart.js visualization of enrollment trends over 12 months
- Upcoming sessions table with available seat indicators
- Expiring certificates panel with color-coded urgency levels
- Top 5 most attended courses ranking
- Quick enrollment modal for rapid employee registration

## Technology Stack

- **Odoo Version**: 18.0
- **Python**: 3.10+
- **Frontend Framework**: OWL (Odoo Web Library)
- **Charting**: Chart.js
- **UI Framework**: Bootstrap 5
- **Database**: PostgreSQL

## Installation

### Prerequisites
- Odoo 18.0 installed and running
- Python 3.10 or higher
- PostgreSQL database
- Dependencies: `base`, `hr`, `mail`, `web`, `portal` modules

### Installation Steps

1. Clone the repository into your Odoo addons directory:
```bash
cd /path/to/odoo/addons
git clone https://github.com/yourusername/employee_training.git
```

2. Restart the Odoo server:
```bash
sudo systemctl restart odoo
# or
./odoo-bin -c /etc/odoo/odoo.conf
```

3. Update the apps list in Odoo:
   - Navigate to Apps menu
   - Click "Update Apps List"
   - Remove the "Apps" filter

4. Install the module:
   - Search for "Employee Training"
   - Click "Install"

### Post-Installation

The module automatically:
- Creates menu structure under "Training"
- Sets up security groups and access rules
- Installs demo data (5 courses, 10 sessions)
- Configures daily cron job for certificate expiry monitoring

## Configuration

### Setting Up Training Courses

1. Navigate to **Training → Courses → Training Courses**
2. Click **Create** and fill in:
   - Course Name
   - Description
   - Duration (in days)
   - Check "Is Certification Course" if a certificate should be issued

### Scheduling Sessions

1. Go to **Training → Courses → Training Sessions**
2. Create a new session:
   - Select course
   - Set start and end dates
   - Assign instructor
   - Define capacity
   - Specify location

### Managing Enrollments

1. Navigate to **Training → Enrollments → All Enrollments**
2. Create enrollment for an employee
3. Workflow: Draft → Confirm → Mark Attended
4. Certificate auto-generates for certification courses

### Portal Configuration

Enable portal access for employees:
1. Go to **Settings → Users & Companies → Users**
2. Add user to "Portal" group
3. Employees can now access their enrollments and certificates at `/my`

## Usage

### For HR Managers

**Dashboard Access**
- Navigate to **Training → Dashboard**
- View real-time statistics and trends
- Monitor upcoming sessions and expiring certificates
- Use quick enrollment feature for rapid registration

**Certificate Management**
- Certificates auto-generate when enrollments are marked "Attended"
- Print certificates via "Print Certificate" button
- Monitor expiry dates in dashboard and certificate views

**Compliance Monitoring**
- Daily cron job checks for certificates expiring within 30 days
- Automatic activity creation for employees and their managers
- Email notifications sent to affected parties

### For Employees (Portal Users)

**Accessing the Portal**
1. Login at `/web/login`
2. Click "My Account" or navigate to `/my`
3. Access:
   - **My Enrollments**: View training schedule and status
   - **My Certificates**: Download PDF certificates

**Downloading Certificates**
- Click on any certificate in "My Certificates"
- Click "Download PDF Certificate" button
- PDF opens in new tab or downloads to device

## Module Structure

```
employee_training/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── training_course.py
│   ├── training_session.py
│   ├── training_enrollment.py
│   └── training_certificate.py
├── views/
│   ├── training_course_views.xml
│   ├── training_session_views.xml
│   ├── training_enrollment_views.xml
│   ├── training_certificate_views.xml
│   ├── training_dashboard_views.xml
│   ├── training_menus.xml
│   └── training_portal_templates.xml
├── controllers/
│   ├── __init__.py
│   └── portal.py
├── security/
│   ├── training_security.xml
│   └── ir.model.access.csv
├── data/
│   ├── training_cron.xml
│   └── mail_template.xml
├── report/
│   ├── training_certificate_report.xml
│   └── training_certificate_template.xml
├── demo/
│   └── training_demo.xml
├── tests/
│   ├── __init__.py
│   ├── test_training_course.py
│   ├── test_training_enrollment.py
│   └── test_training_certificate.py
└── static/
    ├── description/
    │   └── icon.png
    └── src/
        └── components/
            ├── training_dashboard.js
            ├── training_dashboard.xml
            └── training_dashboard.scss
```

## Data Model

### Relationships
```
training.course (1) ──→ (N) training.session
training.session (1) ──→ (N) training.enrollment
hr.employee (1) ──→ (N) training.enrollment
training.enrollment (1) ──→ (1) training.certificate
training.course (1) ──→ (N) training.certificate
```

### Key Models

**training.course**
- Defines training courses with certification requirements
- Tracks associated sessions and issued certificates

**training.session**
- Individual training sessions with dates and capacity
- Computed fields for seat availability
- Constraint validation for capacity limits

**training.enrollment**
- Employee registrations for training sessions
- State workflow management
- Duplicate enrollment prevention

**training.certificate**
- Auto-generated certificates for completed training
- Expiry date computation (+2 years)
- State tracking (valid/expiring_soon/expired)

## Security

### User Groups
- **Training User**: Read-only access to training records
- **Training Manager**: Full CRUD access to all training data

### Record Rules
- Employees can only view their own enrollments and certificates
- HR Managers can view and manage all records
- Portal users have read-only access to their own data

## Testing

Run the test suite:
```bash
./odoo-bin -c odoo.conf -d test_db --test-enable -i employee_training --stop-after-init
```

### Test Coverage
- Model constraint validation
- Workflow state transitions
- Certificate auto-generation logic
- Expiry date calculations
- Security rule enforcement
- Capacity limit validation

## Performance Optimization

- Indexed fields on high-query columns (employee_id, course_id, session_id, dates)
- Stored computed fields for frequently accessed data
- Efficient `read_group` queries for dashboard aggregations
- Lazy loading for related fields
- Optimized cron job queries with date-based filtering

## Customization

### Adjusting Certificate Expiry Period

Edit `models/training_certificate.py`:
```python
def _compute_expiry_date(self):
    # Change years=2 to desired period
    certificate.expiry_date = certificate.issue_date + relativedelta(years=2)
```

### Modifying Notification Threshold

Edit `models/training_certificate.py`:
```python
def _cron_check_expiring_certificates(self):
    # Change days=30 to desired threshold
    expiry_threshold = today + relativedelta(days=30)
```

### Customizing Certificate PDF

Edit `report/training_certificate_template.xml` to modify:
- Layout and styling
- Company branding
- Border designs
- Content sections

## Troubleshooting

### Module Not Appearing in Apps List
- Ensure module is in correct addons path
- Update apps list
- Check `__manifest__.py` for syntax errors
- Verify Odoo logs for loading errors

### Certificate Not Auto-Generating
- Verify course has "Is Certification Course" enabled
- Ensure enrollment state is "Attended"
- Check Odoo logs for errors during creation

### Dashboard Not Loading
- Clear browser cache (Ctrl+Shift+R)
- Verify user has HR Manager access
- Check browser console for JavaScript errors
- Ensure assets are properly loaded

### Portal Access Issues
- Verify user has portal access rights
- Ensure user is linked to employee record
- Check security record rules in logs

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Coding Standards
- Follow Odoo development guidelines
- Write meaningful commit messages
- Add unit tests for new features
- Update documentation as needed
- Ensure code passes linting checks

## Roadmap

Planned enhancements:
- Advanced reporting and analytics
- Skills matrix integration
- Training budget tracking
- External training provider management
- Waiting list functionality for full sessions
- Multi-company support improvements
- Mobile application support
- Integration with learning management systems (LMS)

## License

This project is licensed under the LGPL-3.0 License - see the LICENSE file for details.

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Contact: your.email@example.com
- Documentation: [Link to documentation]

## Acknowledgments

- Built for Odoo 18.0
- Uses Chart.js for data visualization
- Inspired by modern training management best practices

## Changelog

### Version 1.0.0 (Current)
- Initial release
- Core training and certification management
- Interactive OWL dashboard
- Portal access for employees
- PDF certificate generation
- Automated expiry notifications
- Comprehensive test coverage
- Demo data included

---

**Made with Odoo 18.0**
