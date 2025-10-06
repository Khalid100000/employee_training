# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
from collections import defaultdict


class TrainingDashboard(http.Controller):

    @http.route('/training/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self):
        """Get all dashboard data in one call"""
        return {
            'upcoming_sessions': self._get_upcoming_sessions(),
            'expiring_certificates': self._get_expiring_certificates(),
            'top_courses': self._get_top_courses(),
            'enrollments_per_month': self._get_enrollments_per_month(),
            'statistics': self._get_statistics(),
        }

    def _get_upcoming_sessions(self):
        """Get upcoming training sessions with available seats"""
        Session = request.env['training.session']
        today = datetime.now().date()
        
        sessions = Session.search([
            ('start_date', '>=', today),
            ('state', 'in', ['draft', 'scheduled']),
            ('available_seats', '>', 0),
        ], order='start_date asc', limit=10)
        
        return [{
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

    def _get_expiring_certificates(self):
        """Get certificates expiring within 30 days"""
        Certificate = request.env['training.certificate']
        today = datetime.now().date()
        expiry_threshold = today + timedelta(days=30)
        
        certificates = Certificate.search([
            ('expiry_date', '<=', expiry_threshold),
            ('expiry_date', '>=', today),
            ('state', '=', 'expiring_soon'),
        ], order='expiry_date asc', limit=10)
        
        return [{
            'id': cert.id,
            'name': cert.name,
            'employee_name': cert.employee_id.name,
            'course_name': cert.course_id.name,
            'expiry_date': cert.expiry_date.strftime('%Y-%m-%d'),
            'days_until_expiry': cert.days_until_expiry,
        } for cert in certificates]

    def _get_top_courses(self):
        """Get top 5 most attended courses"""
        Enrollment = request.env['training.enrollment']
        
        # Get enrollment counts grouped by course
        enrollment_data = Enrollment.read_group(
            domain=[('state', '=', 'attended')],
            fields=['course_id'],
            groupby=['course_id'],
            orderby='course_id_count desc',
            limit=5
        )
        
        result = []
        for data in enrollment_data:
            course_id = data['course_id'][0] if data['course_id'] else None
            if course_id:
                course = request.env['training.course'].browse(course_id)
                result.append({
                    'id': course_id,
                    'name': data['course_id'][1],
                    'count': data['course_id_count'],
                    'is_certification': course.is_certification,
                })
        
        return result

    def _get_enrollments_per_month(self):
        """Get enrollment statistics per month for the last 12 months"""
        Enrollment = request.env['training.enrollment']
        today = datetime.now().date()
        twelve_months_ago = today - timedelta(days=365)
        
        enrollments = Enrollment.search([
            ('enrollment_date', '>=', twelve_months_ago),
        ])
        
        # Group by month
        monthly_data = defaultdict(lambda: {'confirmed': 0, 'attended': 0, 'cancelled': 0})
        
        for enrollment in enrollments:
            month_key = enrollment.enrollment_date.strftime('%Y-%m')
            monthly_data[month_key][enrollment.state] += 1
        
        # Convert to sorted list
        result = []
        current_date = twelve_months_ago
        while current_date <= today:
            month_key = current_date.strftime('%Y-%m')
            month_label = current_date.strftime('%b %Y')
            
            result.append({
                'month': month_label,
                'confirmed': monthly_data[month_key].get('confirmed', 0),
                'attended': monthly_data[month_key].get('attended', 0),
                'cancelled': monthly_data[month_key].get('cancelled', 0),
            })
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return result

    def _get_statistics(self):
        """Get general statistics"""
        Session = request.env['training.session']
        Enrollment = request.env['training.enrollment']
        Certificate = request.env['training.certificate']
        
        today = datetime.now().date()
        
        return {
            'total_active_sessions': Session.search_count([
                ('state', 'in', ['scheduled', 'ongoing']),
            ]),
            'total_enrollments_this_month': Enrollment.search_count([
                ('enrollment_date', '>=', today.replace(day=1)),
            ]),
            'certificates_expiring_soon': Certificate.search_count([
                ('state', '=', 'expiring_soon'),
            ]),
            'completion_rate': self._calculate_completion_rate(),
        }

    def _calculate_completion_rate(self):
        """Calculate overall completion rate"""
        Enrollment = request.env['training.enrollment']
        
        total = Enrollment.search_count([
            ('state', 'in', ['confirmed', 'attended']),
        ])
        
        if total == 0:
            return 0
        
        attended = Enrollment.search_count([
            ('state', '=', 'attended'),
        ])
        
        return round((attended / total) * 100, 1)

    @http.route('/training/dashboard/sessions', type='json', auth='user')
    def get_sessions_for_enrollment(self):
        """Get available sessions for quick enrollment"""
        Session = request.env['training.session']
        today = datetime.now().date()
        
        sessions = Session.search([
            ('start_date', '>=', today),
            ('state', 'in', ['draft', 'scheduled']),
            ('available_seats', '>', 0),
        ], order='start_date asc')
        
        return [{
            'id': session.id,
            'name': session.name,
            'display_name': f"{session.course_id.name} - {session.start_date}",
        } for session in sessions]

    @http.route('/training/dashboard/employees', type='json', auth='user')
    def get_employees_for_enrollment(self):
        """Get employees for quick enrollment"""
        Employee = request.env['hr.employee']
        
        employees = Employee.search([], order='name asc')
        
        return [{
            'id': emp.id,
            'name': emp.name,
        } for emp in employees]

    @http.route('/training/dashboard/create_enrollment', type='json', auth='user')
    def create_enrollment(self, employee_id, session_id):
        """Create a new enrollment via AJAX"""
        try:
            Enrollment = request.env['training.enrollment']
            
            enrollment = Enrollment.create({
                'employee_id': employee_id,
                'session_id': session_id,
            })
            
            # Auto-confirm
            enrollment.action_confirm()
            
            return {
                'success': True,
                'message': f'Enrollment created and confirmed for {enrollment.employee_id.name}',
                'enrollment_id': enrollment.id,
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e),
            }