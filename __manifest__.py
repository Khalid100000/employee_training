{
    'name': 'Employee Training & Certification',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Manage employee training programs, certifications, and compliance',
    'description': """
        Employee Training & Certification Management
        ============================================
        * Manage training courses and sessions
        * Track employee enrollments and attendance
        * Issue and manage certificates with expiry tracking
        * Automated compliance notifications
        * Employee portal access
        * PDF certificate generation
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'hr',
        'mail',
        'web',
        'portal',
    ],
    'data': [
        # Security
        'security/training_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/training_cron.xml',
        'data/mail_template.xml',
        
        # Views
        'views/training_course_views.xml',
        'views/training_session_views.xml',
        'views/training_enrollment_views.xml',
        'views/training_certificate_views.xml',
        'views/training_dashboard_views.xml',
        'views/training_menus.xml',
        'views/training_portal_templates.xml',
        
        # Reports
        'report/training_certificate_report.xml',
        'report/training_certificate_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'employee_training/static/src/components/training_dashboard.js',
            'employee_training/static/src/components/training_dashboard.xml',
            'employee_training/static/src/components/training_dashboard.scss',
            # Chart.js is available globally in Odoo
            ('include', 'web._assets_primary_variables'),
        ],
    },
    'demo': [
        'demo/training_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}