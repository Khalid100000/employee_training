# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from datetime import datetime

class TrainingSession(models.Model):
    _name = 'training.session'
    _description = 'Training Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'

    name = fields.Char(
        string='Session Name',
        compute='_compute_name',
        store=True,
        index=True
    )
    course_id = fields.Many2one(
        comodel_name='training.course',
        string='Course',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True
    )
    instructor_id = fields.Many2one(
        comodel_name='res.users',
        string='Instructor',
        tracking=True
    )
    start_date = fields.Date(
        string='Start Date',
        required=True,
        tracking=True,
        index=True
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        tracking=True
    )
    location = fields.Char(
        string='Location',
        help='Physical or virtual location of the training'
    )
    capacity = fields.Integer(
        string='Capacity',
        default=20,
        required=True,
        help='Maximum number of participants'
    )
    enrolled_count = fields.Integer(
        string='Enrolled Count',
        compute='_compute_enrolled_count',
        store=True,
        help='Number of confirmed enrollments'
    )
    available_seats = fields.Integer(
        string='Available Seats',
        compute='_compute_available_seats',
        store=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    # Relational fields
    enrollment_ids = fields.One2many(
        comodel_name='training.enrollment',
        inverse_name='session_id',
        string='Enrollments'
    )

    @api.depends('course_id', 'start_date')
    def _compute_name(self):
        for session in self:
            if session.course_id and session.start_date:
                session.name = f"{session.course_id.name} - {session.start_date}"
            else:
                session.name = 'New Session'

    @api.depends('enrollment_ids', 'enrollment_ids.state')
    def _compute_enrolled_count(self):
        for session in self:
            session.enrolled_count = len(
                session.enrollment_ids.filtered(
                    lambda e: e.state in ['confirmed', 'attended']
                )
            )

    @api.depends('capacity', 'enrolled_count')
    def _compute_available_seats(self):
        for session in self:
            session.available_seats = session.capacity - session.enrolled_count

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for session in self:
            if session.end_date < session.start_date:
                raise exceptions.ValidationError(
                    'End date must be after start date.'
                )

    @api.constrains('capacity')
    def _check_capacity(self):
        for session in self:
            if session.capacity < 1:
                raise exceptions.ValidationError(
                    'Capacity must be at least 1.'
                )

    def action_confirm_schedule(self):
        """Confirm the session schedule"""
        self.write({'state': 'scheduled'})

    def action_start_session(self):
        """Start the session"""
        self.write({'state': 'ongoing'})

    def action_complete_session(self):
        """Complete the session"""
        self.write({'state': 'completed'})

    def action_cancel_session(self):
        """Cancel the session"""
        self.write({'state': 'cancelled'})

    def action_view_enrollments(self):
        """Smart button action to view session enrollments"""
        self.ensure_one()
        return {
            'name': 'Enrollments',
            'type': 'ir.actions.act_window',
            'res_model': 'training.enrollment',
            'view_mode': 'tree,form',
            'domain': [('session_id', '=', self.id)],
            'context': {'default_session_id': self.id}
        }

    @api.model
    def get_dashboard_data(self):
        """Get all dashboard data for OWL component"""
        from datetime import datetime, timedelta
        from collections import defaultdict
        
        today = datetime.now().date()
        
        # Upcoming sessions
        sessions = self.search([
            ('start_date', '>=', today),
            ('state', 'in', ['draft', 'scheduled']),
            ('available_seats', '>', 0),
        ], order='start_date asc', limit=10)
        
        upcoming_sessions = [{
            'id': session.id,
            'name': session.name,
            'course_name': session.course_id.name,
            'start_date': session.start_date.strftime('%Y-%m-%d'),
            'end_date': session.end_date.strftime('%Y-%m-%d'),
            'location': session.location or 'TBD',
            'available_seats': session.available_seats,
            'capacity': session.capacity,
            'instructor': session.instructor_id.name if session.instructor_id else 'TBD',
        } for session in sessions]
        
        # Expiring certificates
        Certificate = self.env['training.certificate']
        expiry_threshold = today + timedelta(days=30)
        
        certificates = Certificate.search([
            ('expiry_date', '<=', expiry_threshold),
            ('expiry_date', '>=', today),
            ('state', '=', 'expiring_soon'),
        ], order='expiry_date asc', limit=10)
        
        expiring_certificates = [{
            'id': cert.id,
            'name': cert.name,
            'employee_name': cert.employee_id.name,
            'course_name': cert.course_id.name,
            'expiry_date': cert.expiry_date.strftime('%Y-%m-%d'),
            'days_until_expiry': cert.days_until_expiry,
        } for cert in certificates]
        
        # Top courses
        Enrollment = self.env['training.enrollment']
        enrollment_data = Enrollment.read_group(
            domain=[('state', '=', 'attended')],
            fields=['course_id'],
            groupby=['course_id'],
            orderby='course_id_count desc',
            limit=5
        )
        
        top_courses = []
        for data in enrollment_data:
            if data['course_id']:
                course = self.env['training.course'].browse(data['course_id'][0])
                top_courses.append({
                    'id': course.id,
                    'name': data['course_id'][1],
                    'count': data['course_id_count'],
                    'is_certification': course.is_certification,
                })
        
        # Enrollments per month
        twelve_months_ago = today - timedelta(days=365)
        enrollments = Enrollment.search([
            ('enrollment_date', '>=', twelve_months_ago),
        ])
        
        monthly_data = defaultdict(lambda: {'confirmed': 0, 'attended': 0, 'cancelled': 0})
        for enrollment in enrollments:
            month_key = enrollment.enrollment_date.strftime('%Y-%m')
            if enrollment.state in monthly_data[month_key]:
                monthly_data[month_key][enrollment.state] += 1
        
        enrollments_per_month = []
        current_date = twelve_months_ago
        while current_date <= today:
            month_key = current_date.strftime('%Y-%m')
            month_label = current_date.strftime('%b %Y')
            
            enrollments_per_month.append({
                'month': month_label,
                'confirmed': monthly_data[month_key].get('confirmed', 0),
                'attended': monthly_data[month_key].get('attended', 0),
                'cancelled': monthly_data[month_key].get('cancelled', 0),
            })
            
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        # Statistics
        total_active_sessions = self.search_count([
            ('state', 'in', ['scheduled', 'ongoing']),
        ])
        
        total_enrollments_this_month = Enrollment.search_count([
            ('enrollment_date', '>=', today.replace(day=1)),
        ])
        
        certificates_expiring_soon = Certificate.search_count([
            ('state', '=', 'expiring_soon'),
        ])
        
        total_confirmed = Enrollment.search_count([
            ('state', 'in', ['confirmed', 'attended']),
        ])
        attended = Enrollment.search_count([
            ('state', '=', 'attended'),
        ])
        completion_rate = round((attended / total_confirmed) * 100, 1) if total_confirmed > 0 else 0
        
        return {
            'upcoming_sessions': upcoming_sessions,
            'expiring_certificates': expiring_certificates,
            'top_courses': top_courses,
            'enrollments_per_month': enrollments_per_month,
            'statistics': {
                'total_active_sessions': total_active_sessions,
                'total_enrollments_this_month': total_enrollments_this_month,
                'certificates_expiring_soon': certificates_expiring_soon,
                'completion_rate': completion_rate,
            }
        }

    @api.model
    def get_available_sessions(self):
        """Get available sessions for enrollment dropdown"""
        today = datetime.now().date()
        
        sessions = self.search([
            ('start_date', '>=', today),
            ('state', 'in', ['draft', 'scheduled']),
            ('available_seats', '>', 0),
        ], order='start_date asc')
        
        return [{
            'id': session.id,
            'name': session.name,
            'display_name': f"{session.course_id.name} - {session.start_date}",
        } for session in sessions]