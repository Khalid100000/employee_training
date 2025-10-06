# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _


class TrainingEnrollment(models.Model):
    _name = 'training.enrollment'
    _description = 'Training Enrollment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True
    )
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True
    )
    session_id = fields.Many2one(
        comodel_name='training.session',
        string='Training Session',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True
    )
    course_id = fields.Many2one(
        comodel_name='training.course',
        string='Course',
        related='session_id.course_id',
        store=True,
        index=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('attended', 'Attended'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, index=True)
    
    enrollment_date = fields.Date(
        string='Enrollment Date',
        default=fields.Date.context_today,
        required=True
    )
    notes = fields.Text(
        string='Notes'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    # Related fields for portal
    start_date = fields.Date(
        string='Start Date',
        related='session_id.start_date',
        store=True
    )
    end_date = fields.Date(
        string='End Date',
        related='session_id.end_date',
        store=True
    )

    @api.depends('employee_id', 'session_id')
    def _compute_name(self):
        for enrollment in self:
            if enrollment.employee_id and enrollment.session_id:
                enrollment.name = f"{enrollment.employee_id.name} - {enrollment.session_id.name}"
            else:
                enrollment.name = 'New Enrollment'

    def _compute_access_url(self):
        """Compute portal access URL"""
        super()._compute_access_url()
        for enrollment in self:
            enrollment.access_url = f'/my/enrollments/{enrollment.id}'

    @api.constrains('employee_id', 'session_id', 'state')
    def _check_unique_enrollment(self):
        """Prevent duplicate enrollments for same employee in same session"""
        for enrollment in self:
            if enrollment.state != 'cancelled':
                duplicate = self.search([
                    ('id', '!=', enrollment.id),
                    ('employee_id', '=', enrollment.employee_id.id),
                    ('session_id', '=', enrollment.session_id.id),
                    ('state', '!=', 'cancelled')
                ], limit=1)
                if duplicate:
                    raise exceptions.ValidationError(
                        f"Employee {enrollment.employee_id.name} is already enrolled in this session."
                    )

    @api.constrains('session_id', 'state')
    def _check_capacity(self):
        """Ensure session capacity is not exceeded when confirming enrollment"""
        for enrollment in self:
            if enrollment.state in ['confirmed', 'attended']:
                if enrollment.session_id.enrolled_count > enrollment.session_id.capacity:
                    raise exceptions.ValidationError(
                        f"Cannot confirm enrollment. Session capacity ({enrollment.session_id.capacity}) has been reached."
                    )

    def action_confirm(self):
        """Confirm enrollment"""
        for enrollment in self:
            if enrollment.session_id.available_seats <= 0:
                raise exceptions.UserError(
                    f"No available seats. Capacity: {enrollment.session_id.capacity}, "
                    f"Enrolled: {enrollment.session_id.enrolled_count}"
                )
            enrollment.state = 'confirmed'
            enrollment.message_post(
                body=_("Enrollment confirmed for %s", enrollment.employee_id.name)
            )

    def action_mark_attended(self):
        """Mark enrollment as attended and generate certificate if applicable"""
        for enrollment in self:
            enrollment.state = 'attended'
            enrollment.message_post(
                body=_("%s attended the training", enrollment.employee_id.name)
            )
            # Generate certificate if certification course
            if enrollment.course_id.is_certification:
                enrollment._generate_certificate()

    def action_cancel(self):
        """Cancel enrollment"""
        for enrollment in self:
            enrollment.state = 'cancelled'
            enrollment.message_post(
                body=_("Enrollment cancelled for %s", enrollment.employee_id.name)
            )

    def action_reset_to_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})

    def _generate_certificate(self):
        """Generate certificate for attended enrollment (if certification course)"""
        self.ensure_one()
        if self.state == 'attended' and self.course_id.is_certification:
            # Check if certificate already exists
            existing_cert = self.env['training.certificate'].search([
                ('employee_id', '=', self.employee_id.id),
                ('course_id', '=', self.course_id.id),
                ('enrollment_id', '=', self.id)
            ], limit=1)
            
            if not existing_cert:
                cert = self.env['training.certificate'].create({
                    'employee_id': self.employee_id.id,
                    'course_id': self.course_id.id,
                    'enrollment_id': self.id,
                })
                self.message_post(
                    body=_("Certificate %s generated", cert.name)
                )
                return cert
        return False