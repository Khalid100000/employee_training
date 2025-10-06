# -*- coding: utf-8 -*-

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError, AccessError
from odoo import fields


class TestTrainingCertificate(TransactionCase):
    """Test cases for training.certificate model"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Certificate = cls.env['training.certificate']
        cls.Course = cls.env['training.course']
        cls.Employee = cls.env['hr.employee']
        cls.User = cls.env['res.users']
        
        # Create certification course
        cls.course = cls.Course.create({
            'name': 'Test Certification Course',
            'duration_days': 1,
            'is_certification': True,
        })
        
        # Create non-certification course
        cls.non_cert_course = cls.Course.create({
            'name': 'Test Regular Course',
            'duration_days': 1,
            'is_certification': False,
        })
        
        # Create employees with users for security testing
        cls.user1 = cls.User.create({
            'name': 'Test User 1',
            'login': 'testuser1',
            'email': 'testuser1@test.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        
        cls.employee1 = cls.Employee.create({
            'name': 'Test Employee 1',
            'user_id': cls.user1.id,
        })
        
        cls.user2 = cls.User.create({
            'name': 'Test User 2',
            'login': 'testuser2',
            'email': 'testuser2@test.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        
        cls.employee2 = cls.Employee.create({
            'name': 'Test Employee 2',
            'user_id': cls.user2.id,
        })
        
    def test_01_certificate_creation(self):
        """Test basic certificate creation and sequence generation"""
        certificate = self.Certificate.create({
            'employee_id': self.employee1.id,
            'course_id': self.course.id,
        })
        self.assertTrue(certificate, "Certificate should be created")
        self.assertNotEqual(certificate.name, 'New', "Certificate number should be generated")
        self.assertEqual(certificate.state, 'valid', "New certificate should be in valid state")
        
    def test_02_expiry_date_computation(self):
        """Test expiry date computation for certification courses (+2 years)"""
        today = date.today()
        certificate = self.Certificate.create({
            'employee_id': self.employee1.id,
            'course_id': self.course.id,
            'issue_date': today,
        })
        
        # Force compute stored fields
        certificate.flush_recordset()
        certificate.invalidate_recordset()
        
        expected_expiry = today + relativedelta(years=2)
        self.assertEqual(
            certificate.expiry_date, 
            expected_expiry,
            f"Expiry date should be +2 years from issue date. Expected: {expected_expiry}, Got: {certificate.expiry_date}"
        )
        
    def test_03_no_expiry_for_non_certification(self):
        """Test that non-certification courses don't get expiry dates"""
        certificate = self.Certificate.create({
            'employee_id': self.employee1.id,
            'course_id': self.non_cert_course.id,
            'issue_date': date.today(),
        })
        
        certificate.flush_recordset()
        certificate.invalidate_recordset()
        
        self.assertFalse(
            certificate.expiry_date,
            "Non-certification courses should not have expiry dates"
        )
        
    def test_04_certificate_state_valid(self):
        """Test certificate state when far from expiry"""
        today = date.today()
        certificate = self.Certificate.create({
            'employee_id': self.employee1.id,
            'course_id': self.course.id,
            'issue_date': today,
        })
        
        certificate.flush_recordset()
        certificate.invalidate_recordset()
        
        self.assertEqual(certificate.state, 'valid', "Certificate should be in valid state")
        self.assertFalse(certificate.is_expired, "Certificate should not be expired")
        self.assertGreater(certificate.days_until_expiry, 30, "Should have more than 30 days until expiry")
        
    def test_05_certificate_state_expiring_soon(self):
        """Test certificate state when expiring within 30 days"""
        # Issue certificate almost 2 years ago (with 20 days remaining)
        issue_date = date.today() - relativedelta(years=2) + timedelta(days=20)
        
        certificate = self.Certificate.create({
            'employee_id': self.employee1.id,
            'course_id': self.course.id,
            'issue_date': issue_date,
        })
        
        certificate.flush_recordset()
        certificate.invalidate_recordset()
        
        self.assertEqual(
            certificate.state, 
            'expiring_soon',
            f"Certificate should be expiring soon. Days until expiry: {certificate.days_until_expiry}"
        )
        self.assertFalse(certificate.is_expired, "Certificate should not be expired yet")
        self.assertLessEqual(certificate.days_until_expiry, 30, "Should have 30 or fewer days until expiry")
        
    def test_06_certificate_state_expired(self):
        """Test certificate state when expired"""
        # Issue certificate over 2 years ago
        issue_date = date.today() - relativedelta(years=2, days=10)
        
        certificate = self.Certificate.create({
            'employee_id': self.employee1.id,
            'course_id': self.course.id,
            'issue_date': issue_date,
        })
        
        certificate.flush_recordset()
        certificate.invalidate_recordset()
        
        self.assertEqual(certificate.state, 'expired', "Certificate should be expired")
        self.assertTrue(certificate.is_expired, "is_expired flag should be True")
        self.assertLess(certificate.days_until_expiry, 0, "Days until expiry should be negative")
        
    def test_07_cron_finds_expiring_certificates(self):
        """Test cron job identifies and notifies expiring certificates"""
        # Create certificate expiring in 15 days
        issue_date = date.today() - relativedelta(years=2) + timedelta(days=15)
        
        certificate = self.Certificate.create({
            'employee_id': self.employee1.id,
            'course_id': self.course.id,
            'issue_date': issue_date,
            'expiry_notified': False,
        })
        
        certificate.flush_recordset()
        certificate.invalidate_recordset()
        
        # Verify initial state
        self.assertEqual(certificate.state, 'expiring_soon', "Certificate should be expiring soon")
        self.assertFalse(certificate.expiry_notified, "Should not be notified yet")
        
        # Run cron job
        self.Certificate._cron_check_expiring_certificates()
        
        # Refresh record
        certificate.invalidate_recordset()
        
        # Verify notification was sent
        self.assertTrue(certificate.expiry_notified, "Expiry notification should be marked as sent")
        
    def test_08_cron_does_not_notify_twice(self):
        """Test cron doesn't send duplicate notifications"""
        issue_date = date.today() - relativedelta(years=2) + timedelta(days=15)
        
        certificate = self.Certificate.create({
            'employee_id': self.employee1.id,
            'course_id': self.course.id,
            'issue_date': issue_date,
            'expiry_notified': True,  # Already notified
        })
        
        # Run cron
        self.Certificate._cron_check_expiring_certificates()
        
        # Should still be True (not changed)
        certificate.invalidate_recordset()
        self.assertTrue(certificate.expiry_notified, "Should remain notified")
        
    def test_09_renew_certificate(self):
        """Test certificate renewal creates new certificate"""
        old_certificate = self.Certificate.create({
            'employee_id': self.employee1.id,
            'course_id': self.course.id,
            'issue_date': date.today() - relativedelta(years=2),
        })
        
        # Get the action dictionary
        action = old_certificate.action_renew_certificate()
        
        # Get the new certificate
        new_certificate = self.Certificate.browse(action['res_id'])
        
        self.assertTrue(new_certificate.exists(), "New certificate should be created")
        self.assertEqual(new_certificate.employee_id, old_certificate.employee_id, "Should be for same employee")
        self.assertEqual(new_certificate.course_id, old_certificate.course_id, "Should be for same course")
        self.assertEqual(new_certificate.issue_date, date.today(), "Should have today's issue date")
        self.assertFalse(new_certificate.expiry_notified, "New certificate should not be notified")
        self.assertNotEqual(new_certificate.id, old_certificate.id, "Should be a different record")


class TestTrainingCourse(TransactionCase):
    """Test cases for training.course model"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Course = cls.env['training.course']
        cls.Session = cls.env['training.session']
        
    def test_01_create_course(self):
        """Test basic course creation"""
        course = self.Course.create({
            'name': 'Test Course',
            'description': 'Test Description',
            'duration_days': 3,
            'is_certification': True,
        })
        self.assertTrue(course, "Course should be created")
        self.assertEqual(course.name, 'Test Course')
        self.assertEqual(course.duration_days, 3)
        self.assertTrue(course.is_certification)
        self.assertTrue(course.active, "Course should be active by default")
        
    def test_02_course_session_count(self):
        """Test session count computation"""
        course = self.Course.create({
            'name': 'Test Course',
            'duration_days': 1,
        })
        
        course.flush_recordset()
        course.invalidate_recordset()
        
        self.assertEqual(course.session_count, 0, "New course should have 0 sessions")
        
        # Create sessions
        self.Session.create({
            'course_id': course.id,
            'start_date': date.today(),
            'end_date': date.today(),
            'capacity': 10,
        })
        
        course.invalidate_recordset()
        self.assertEqual(course.session_count, 1, "Should have 1 session")
        
        self.Session.create({
            'course_id': course.id,
            'start_date': date.today() + timedelta(days=7),
            'end_date': date.today() + timedelta(days=7),
            'capacity': 10,
        })
        
        course.invalidate_recordset()
        self.assertEqual(course.session_count, 2, "Should have 2 sessions")
        
    def test_03_course_certificate_count(self):
        """Test certificate count computation"""
        course = self.Course.create({
            'name': 'Test Course',
            'is_certification': True,
        })
        
        employee = self.env['hr.employee'].create({'name': 'Test Employee'})
        
        self.assertEqual(course.certificate_count, 0, "Should have no certificates initially")
        
        # Create certificate
        self.env['training.certificate'].create({
            'employee_id': employee.id,
            'course_id': course.id,
        })
        
        course.invalidate_recordset()
        self.assertEqual(course.certificate_count, 1, "Should have 1 certificate")


class TestTrainingSession(TransactionCase):
    """Test cases for training.session model"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Course = cls.env['training.course']
        cls.Session = cls.env['training.session']
        cls.User = cls.env['res.users']
        
        cls.course = cls.Course.create({
            'name': 'Test Course',
            'duration_days': 1,
        })
        
        cls.instructor = cls.User.create({
            'name': 'Test Instructor',
            'login': 'instructor@test.com',
            'email': 'instructor@test.com',
        })
        
    def test_01_session_creation(self):
        """Test basic session creation"""
        session = self.Session.create({
            'course_id': self.course.id,
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=1),
            'capacity': 20,
            'location': 'Room 101',
        })
        self.assertTrue(session)
        self.assertEqual(session.state, 'draft', "New session should be in draft state")
        self.assertEqual(session.available_seats, 20, "All seats should be available initially")
        
    def test_02_session_name_computation(self):
        """Test session name is computed correctly"""
        start = date.today()
        session = self.Session.create({
            'course_id': self.course.id,
            'start_date': start,
            'end_date': start,
            'capacity': 10,
        })
        
        session.flush_recordset()
        session.invalidate_recordset()
        
        expected_name = f"{self.course.name} - {start}"
        self.assertEqual(session.name, expected_name, "Session name should be Course - Date")
        
    def test_03_date_constraint(self):
        """Test end_date must be after start_date"""
        with self.assertRaises(ValidationError, msg="Should raise ValidationError for invalid dates"):
            self.Session.create({
                'course_id': self.course.id,
                'start_date': date.today(),
                'end_date': date.today() - timedelta(days=1),  # End before start
                'capacity': 10,
            })
            
    def test_04_capacity_constraint(self):
        """Test capacity must be at least 1"""
        with self.assertRaises(ValidationError, msg="Should raise ValidationError for capacity < 1"):
            self.Session.create({
                'course_id': self.course.id,
                'start_date': date.today(),
                'end_date': date.today(),
                'capacity': 0,  # Invalid capacity
            })
            
    def test_05_session_workflow(self):
        """Test session state transitions"""
        session = self.Session.create({
            'course_id': self.course.id,
            'start_date': date.today(),
            'end_date': date.today(),
            'capacity': 10,
        })
        
        # Draft -> Scheduled
        session.action_confirm_schedule()
        self.assertEqual(session.state, 'scheduled', "Should be in scheduled state")
        
        # Scheduled -> Ongoing
        session.action_start_session()
        self.assertEqual(session.state, 'ongoing', "Should be in ongoing state")
        
        # Ongoing -> Completed
        session.action_complete_session()
        self.assertEqual(session.state, 'completed', "Should be in completed state")
        
    def test_06_session_cancellation(self):
        """Test session can be cancelled"""
        session = self.Session.create({
            'course_id': self.course.id,
            'start_date': date.today(),
            'end_date': date.today(),
            'capacity': 10,
        })
        
        session.action_cancel_session()
        self.assertEqual(session.state, 'cancelled', "Should be in cancelled state")


class TestTrainingEnrollment(TransactionCase):
    """Test cases for training.enrollment model"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Course = cls.env['training.course']
        cls.Session = cls.env['training.session']
        cls.Enrollment = cls.env['training.enrollment']
        cls.Employee = cls.env['hr.employee']
        cls.Certificate = cls.env['training.certificate']
        
        # Create test data
        cls.course = cls.Course.create({
            'name': 'Test Certification Course',
            'duration_days': 1,
            'is_certification': True,
        })
        
        cls.non_cert_course = cls.Course.create({
            'name': 'Regular Course',
            'duration_days': 1,
            'is_certification': False,
        })
        
        cls.session = cls.Session.create({
            'course_id': cls.course.id,
            'start_date': date.today() + timedelta(days=7),
            'end_date': date.today() + timedelta(days=7),
            'capacity': 2,
        })
        
        cls.non_cert_session = cls.Session.create({
            'course_id': cls.non_cert_course.id,
            'start_date': date.today() + timedelta(days=7),
            'end_date': date.today() + timedelta(days=7),
            'capacity': 5,
        })
        
        cls.employee1 = cls.Employee.create({'name': 'Test Employee 1'})
        cls.employee2 = cls.Employee.create({'name': 'Test Employee 2'})
        cls.employee3 = cls.Employee.create({'name': 'Test Employee 3'})
        
    def test_01_enrollment_creation(self):
        """Test basic enrollment creation"""
        enrollment = self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.session.id,
        })
        self.assertTrue(enrollment, "Enrollment should be created")
        self.assertEqual(enrollment.state, 'draft', "New enrollment should be in draft state")
        self.assertEqual(enrollment.course_id, self.course, "Course should be related from session")
        
    def test_02_enrollment_name_computation(self):
        """Test enrollment name is computed correctly"""
        enrollment = self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.session.id,
        })
        
        enrollment.flush_recordset()
        enrollment.invalidate_recordset()
        
        expected_name = f"{self.employee1.name} - {self.session.name}"
        self.assertEqual(enrollment.name, expected_name, "Enrollment name should be Employee - Session")
        
    def test_03_enrollment_workflow_complete(self):
        """Test complete enrollment workflow: draft -> confirmed -> attended"""
        enrollment = self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.session.id,
        })
        
        # Confirm
        enrollment.action_confirm()
        self.assertEqual(enrollment.state, 'confirmed', "Should be in confirmed state")
        
        # Verify session enrolled count updated
        self.session.invalidate_recordset()
        self.assertEqual(self.session.enrolled_count, 1, "Session should have 1 enrolled participant")
        self.assertEqual(self.session.available_seats, 1, "Should have 1 available seat remaining")
        
        # Mark attended
        enrollment.action_mark_attended()
        self.assertEqual(enrollment.state, 'attended', "Should be in attended state")
        
    def test_04_enrollment_cancellation(self):
        """Test enrollment can be cancelled and seat becomes available"""
        enrollment = self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.session.id,
        })
        enrollment.action_confirm()
        
        self.session.invalidate_recordset()
        initial_enrolled = self.session.enrolled_count
        
        # Cancel enrollment
        enrollment.action_cancel()
        self.assertEqual(enrollment.state, 'cancelled', "Should be in cancelled state")
        
        # Verify seat is available again
        self.session.invalidate_recordset()
        self.assertEqual(
            self.session.enrolled_count, 
            initial_enrolled - 1,
            "Enrolled count should decrease after cancellation"
        )
        
    def test_05_capacity_constraint_enforced(self):
        """Test session capacity is enforced - cannot confirm beyond capacity"""
        # Fill capacity (2 seats)
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
        
        self.session.invalidate_recordset()
        self.assertEqual(self.session.enrolled_count, 2, "Should have 2 enrolled")
        self.assertEqual(self.session.available_seats, 0, "Should have 0 available seats")
        
        # Try to add third enrollment (should fail)
        enrollment3 = self.Enrollment.create({
            'employee_id': self.employee3.id,
            'session_id': self.session.id,
        })
        
        with self.assertRaises(UserError, msg="Should raise UserError when capacity exceeded"):
            enrollment3.action_confirm()
            
    def test_06_duplicate_enrollment_prevented(self):
        """Test duplicate enrollment prevention for same employee in same session"""
        self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.session.id,
        })
        
        # Try to create duplicate
        with self.assertRaises(ValidationError, msg="Should raise ValidationError for duplicate enrollment"):
            self.Enrollment.create({
                'employee_id': self.employee1.id,
                'session_id': self.session.id,
            })
            
    def test_07_cancelled_enrollment_allows_duplicate(self):
        """Test that cancelled enrollments don't prevent new enrollment"""
        enrollment1 = self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.session.id,
        })
        enrollment1.action_cancel()
        
        # Should be able to create new enrollment after cancelling
        enrollment2 = self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.session.id,
        })
        self.assertTrue(enrollment2, "Should allow new enrollment after cancellation")
        
    def test_08_certificate_generation_on_attendance(self):
        """Test certificate auto-generation when marking enrollment as attended (certification course)"""
        enrollment = self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.session.id,
        })
        enrollment.action_confirm()
        enrollment.action_mark_attended()
        
        # Check certificate was created
        certificate = self.Certificate.search([
            ('employee_id', '=', self.employee1.id),
            ('course_id', '=', self.course.id),
            ('enrollment_id', '=', enrollment.id),
        ])
        
        self.assertTrue(certificate.exists(), "Certificate should be created")
        self.assertEqual(len(certificate), 1, "Should create exactly one certificate")
        self.assertEqual(certificate.employee_id, self.employee1, "Certificate should be for correct employee")
        self.assertEqual(certificate.course_id, self.course, "Certificate should be for correct course")
        
    def test_09_no_certificate_for_non_certification_course(self):
        """Test that non-certification courses don't generate certificates"""
        enrollment = self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.non_cert_session.id,
        })
        enrollment.action_confirm()
        enrollment.action_mark_attended()
        
        # Check no certificate was created
        certificate = self.Certificate.search([
            ('employee_id', '=', self.employee1.id),
            ('course_id', '=', self.non_cert_course.id),
        ])
        
        self.assertFalse(certificate.exists(), "No certificate should be created for non-certification course")
        
    def test_10_duplicate_certificate_prevention(self):
        """Test that multiple attended enrollments don't create duplicate certificates"""
        enrollment = self.Enrollment.create({
            'employee_id': self.employee1.id,
            'session_id': self.session.id,
        })
        enrollment.action_confirm()
        enrollment.action_mark_attended()
        
        # Try calling generate certificate again
        enrollment._generate_certificate()
        
        # Should still have only one certificate
        certificates = self.Certificate.search([
            ('employee_id', '=', self.employee1.id),
            ('course_id', '=', self.course.id),
            ('enrollment_id', '=', enrollment.id),
        ])
        
        self.assertEqual(len(certificates), 1, "Should not create duplicate certificates")


class TestSecurity(TransactionCase):
    """Security test cases - employee cannot access another's certificate"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Certificate = cls.env['training.certificate']
        cls.Course = cls.env['training.course']
        cls.Employee = cls.env['hr.employee']
        cls.User = cls.env['res.users']
        
        # Create course
        cls.course = cls.Course.create({
            'name': 'Security Test Course',
            'is_certification': True,
        })
        
        # Create users and employees
        cls.user1 = cls.User.create({
            'name': 'Employee User 1',
            'login': 'emp1@test.com',
            'email': 'emp1@test.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        
        cls.employee1 = cls.Employee.create({
            'name': 'Employee 1',
            'user_id': cls.user1.id,
        })
        
        cls.user2 = cls.User.create({
            'name': 'Employee User 2',
            'login': 'emp2@test.com',
            'email': 'emp2@test.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        
        cls.employee2 = cls.Employee.create({
            'name': 'Employee 2',
            'user_id': cls.user2.id,
        })
        
        # Create certificates for each employee
        cls.certificate1 = cls.Certificate.create({
            'employee_id': cls.employee1.id,
            'course_id': cls.course.id,
        })
        
        cls.certificate2 = cls.Certificate.create({
            'employee_id': cls.employee2.id,
            'course_id': cls.course.id,
        })
        
    def test_01_user_can_access_own_certificate(self):
        """Test that user can access their own certificate"""
        # Access certificate as user1
        try:
            cert = self.certificate1.with_user(self.user1)
            cert_read = cert.read(['name', 'employee_id', 'course_id'])
            self.assertTrue(cert_read, "User should be able to read their own certificate")
        except AccessError:
            self.fail("User should be able to access their own certificate")
            
    def test_02_user_cannot_write_other_certificate(self):
        """Test that user cannot modify another user's certificate"""
        # Try to modify certificate2 as user1
        with self.assertRaises(AccessError, msg="Should raise AccessError when writing to another user's certificate"):
            self.certificate2.with_user(self.user1).write({'notes': 'Unauthorized modification'})
            
    def test_03_user_cannot_unlink_other_certificate(self):
        """Test that user cannot delete another user's certificate"""
        # Try to delete certificate2 as user1
        with self.assertRaises(AccessError, msg="Should raise AccessError when deleting another user's certificate"):
            self.certificate2.with_user(self.user1).unlink()
            
    def test_04_admin_can_access_all_certificates(self):
        """Test that admin can access all certificates"""
        admin_user = self.env.ref('base.user_admin')
        
        # Admin should be able to access both certificates
        try:
            cert1 = self.certificate1.with_user(admin_user)
            cert2 = self.certificate2.with_user(admin_user)
            
            cert1.read(['name'])
            cert2.read(['name'])
            
            self.assertTrue(True, "Admin should be able to access all certificates")
        except AccessError:
            self.fail("Admin should have access to all certificates")


class TestIntegration(TransactionCase):
    """Integration tests for complete workflows"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Course = cls.env['training.course']
        cls.Session = cls.env['training.session']
        cls.Enrollment = cls.env['training.enrollment']
        cls.Employee = cls.env['hr.employee']
        cls.Certificate = cls.env['training.certificate']
        
    def test_01_complete_training_flow(self):
        """Test complete flow: create course -> session -> enrollment -> attendance -> certificate"""
        
        # Create course
        course = self.Course.create({
            'name': 'Integration Test Course',
            'duration_days': 2,
            'is_certification': True,
        })
        
        # Create session
        session = self.Session.create({
            'course_id': course.id,
            'start_date': date.today() + timedelta(days=1),
            'end_date': date.today() + timedelta(days=2),
            'capacity': 5,
        })
        
        # Create employee
        employee = self.Employee.create({'name': 'Integration Test Employee'})
        
        # Create enrollment
        enrollment = self.Enrollment.create({
            'employee_id': employee.id,
            'session_id': session.id,
        })
        
        # Progress through workflow
        enrollment.action_confirm()
        self.assertEqual(enrollment.state, 'confirmed')
        
        session.invalidate_recordset()
        self.assertEqual(session.enrolled_count, 1)
        self.assertEqual(session.available_seats, 4)
        
        # Mark attended
        enrollment.action_mark_attended()
        self.assertEqual(enrollment.state, 'attended')
        
        # Verify certificate created
        certificate = self.Certificate.search([
            ('employee_id', '=', employee.id),
            ('course_id', '=', course.id),
        ])
        
        self.assertTrue(certificate.exists(), "Certificate should be created")
        self.assertEqual(certificate.state, 'valid', "Certificate should be valid")
        
        # Verify expiry date
        expected_expiry = date.today() + relativedelta(years=2)
        certificate.flush_recordset()
        certificate.invalidate_recordset()
        
        self.assertEqual(certificate.expiry_date, expected_expiry, "Certificate should expire in 2 years")
        
    def test_02_session_capacity_management(self):
        """Test session capacity management with multiple enrollments"""
        course = self.Course.create({
            'name': 'Capacity Test Course',
            'duration_days': 1,
        })
        
        session = self.Session.create({
            'course_id': course.id,
            'start_date': date.today(),
            'end_date': date.today(),
            'capacity': 3,
        })
        
        # Create 3 employees
        employees = self.Employee.create([
            {'name': 'Employee A'},
            {'name': 'Employee B'},
            {'name': 'Employee C'},
        ])
        
        # Enroll all 3
        for employee in employees:
            enrollment = self.Enrollment.create({
                'employee_id': employee.id,
                'session_id': session.id,
            })
            enrollment.action_confirm()
            
        session.invalidate_recordset()
        self.assertEqual(session.enrolled_count, 3, "Should have 3 enrolled")
        self.assertEqual(session.available_seats, 0, "Should have no available seats")
        
        # Try to enroll 4th employee
        employee4 = self.Employee.create({'name': 'Employee D'})
        enrollment4 = self.Enrollment.create({
            'employee_id': employee4.id,
            'session_id': session.id,
        })
        
        with self.assertRaises(UserError):
            enrollment4.action_confirm()
