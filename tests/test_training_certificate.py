# -*- coding: utf-8 -*-

from datetime import date, timedelta
from odoo.tests.common import TransactionCase


class TestTrainingCertificate(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Certificate = self.env['training.certificate']
        self.Course = self.env['training.course']
        self.Employee = self.env['hr.employee']
        
        self.course = self.Course.create({
            'name': 'Test Course',
            'duration_days': 1,
            'is_certification': True,
        })
        
        self.employee = self.Employee.create({
            'name': 'Test Employee',
        })
        
    def test_certificate_creation(self):
        """Test basic certificate creation"""
        certificate = self.Certificate.create({
            'employee_id': self.employee.id,
            'course_id': self.course.id,
        })
        self.assertTrue(certificate)
        self.assertNotEqual(certificate.name, 'New')
        
    def test_expiry_date_computation(self):
        """Test expiry date is computed (+2 years)"""
        today = date.today()
        certificate = self.Certificate.create({
            'employee_id': self.employee.id,
            'course_id': self.course.id,
            'issue_date': today,
        })
        
        expected_expiry = date(today.year + 2, today.month, today.day)
        self.assertEqual(certificate.expiry_date, expected_expiry)
        
    def test_certificate_state_valid(self):
        """Test certificate state when far from expiry"""
        certificate = self.Certificate.create({
            'employee_id': self.employee.id,
            'course_id': self.course.id,
            'issue_date': date.today(),
        })
        self.assertEqual(certificate.state, 'valid')
        
    def test_certificate_state_expiring_soon(self):
        """Test certificate state when expiring within 30 days"""
        issue_date = date.today() - timedelta(days=700)  # Almost 2 years ago
        certificate = self.Certificate.create({
            'employee_id': self.employee.id,
            'course_id': self.course.id,
            'issue_date': issue_date,
        })
        self.assertEqual(certificate.state, 'expiring_soon')
        
    def test_certificate_state_expired(self):
        """Test certificate state when expired"""
        issue_date = date.today() - timedelta(days=800)  # Over 2 years ago
        certificate = self.Certificate.create({
            'employee_id': self.employee.id,
            'course_id': self.course.id,
            'issue_date': issue_date,
        })
        self.assertEqual(certificate.state, 'expired')
        self.assertTrue(certificate.is_expired)
        
    def test_cron_finds_expiring_certificates(self):
        """Test cron job identifies expiring certificates"""
        # Create certificate expiring in 15 days
        issue_date = date.today() - timedelta(days=715)
        certificate = self.Certificate.create({
            'employee_id': self.employee.id,
            'course_id': self.course.id,
            'issue_date': issue_date,
            'expiry_notified': False,
        })
        
        # Run cron
        self.Certificate._cron_check_expiring_certificates()
        
        # Check notification was sent
        certificate.refresh()
        self.assertTrue(certificate.expiry_notified)