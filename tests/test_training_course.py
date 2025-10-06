# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestTrainingCourse(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Course = self.env['training.course']
        
    def test_create_course(self):
        """Test basic course creation"""
        course = self.Course.create({
            'name': 'Test Course',
            'description': 'Test Description',
            'duration_days': 3,
            'is_certification': True,
        })
        self.assertTrue(course)
        self.assertEqual(course.name, 'Test Course')
        self.assertEqual(course.duration_days, 3)
        self.assertTrue(course.is_certification)
        
    def test_course_session_count(self):
        """Test session count computation"""
        course = self.Course.create({
            'name': 'Test Course',
            'duration_days': 1,
        })
        self.assertEqual(course.session_count, 0)
        
        # Create sessions
        self.env['training.session'].create({
            'course_id': course.id,
            'start_date': '2025-01-01',
            'end_date': '2025-01-01',
            'capacity': 10,
        })
        self.assertEqual(course.session_count, 1)