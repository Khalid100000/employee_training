# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestTrainingEnrollment(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Course = self.env['training.course']
        self.Session = self.env['training.session']
        self.Enrollment = self.env['training.enrollment']
        self.Employee = self.env['hr.employee']
        
        # Create test data
        self.course = self.Course.create({
            'name': 'Test Course',
            'duration_days': 1,
            'is_certification': True,
        })
        
        self.session = self.Session.create({
            'course_id': self.course.id,
            'start_date': '2025-06-01',
            'end_date': '2025-06-01',
            'capacity': 2,
        })
        
        self.employee1 = self.Employee.create({
            'name': 'Test Employee 1',
        })
        
        self.employee2 = self.Employee.create({
            'name': 'Test Employee 2',
        })
        
    def test_enrollment_creation(self):
        """Test basic enrollment creation"""
        enrollment = self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.session.id,
        })
        self.assertTrue(enrollment)
        self.assertEqual(enrollment.state, 'draft')
        
    def test_enrollment_workflow(self):
        """Test enrollment state transitions"""
        enrollment = self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.session.id,
        })
        
        # Confirm
        enrollment.action_confirm()
        self.assertEqual(enrollment.state, 'confirmed')
        self.assertEqual(self.session.enrolled_count, 1)
        
        # Mark attended
        enrollment.action_mark_attended()
        self.assertEqual(enrollment.state, 'attended')
        
    def test_capacity_constraint(self):
        """Test session capacity is enforced"""
        # Create 2 enrollments (at capacity)
        enrollment1 = self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.session.id,
        })
        enrollment1.action_confirm()
        
        enrollment2 = self.Enrollment.create({
            'employee_id': self.employee2.id,
            'session_id': self.session.id,
        })
        enrollment2.action_confirm()
        
        # Try to add third enrollment (should fail)
        employee3 = self.Employee.create({'name': 'Test Employee 3'})
        enrollment3 = self.Enrollment.create({
            'employee_id': employee3.id,
            'session_id': self.session.id,
        })
        
        with self.assertRaises(UserError):
            enrollment3.action_confirm()
            
    def test_duplicate_enrollment_prevented(self):
        """Test duplicate enrollment prevention"""
        self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.session.id,
        })
        
        # Try to create duplicate
        with self.assertRaises(ValidationError):
            self.Enrollment.create({
                'employee_id': self.employee1.id,
                'session_id': self.session.id,
            })
            
    def test_certificate_generation(self):
        """Test certificate auto-generation on attendance"""
        enrollment = self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.session.id,
        })
        enrollment.action_confirm()
        enrollment.action_mark_attended()
        
        # Check certificate was created
        certificate = self.env['training.certificate'].search([
            ('employee_id', '=', self.employee1.id),
            ('course_id', '=', self.course.id),
        ])
        self.assertTrue(certificate)
        self.assertEqual(len(certificate), 1)