# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TrainingCourse(models.Model):
    _name = 'training.course'
    _description = 'Training Course'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Course Name',
        required=True,
        tracking=True,
        index=True
    )
    description = fields.Text(
        string='Description'
    )
    duration_days = fields.Integer(
        string='Duration (Days)',
        default=1,
        help='Duration of the course in days'
    )
    is_certification = fields.Boolean(
        string='Is Certification Course',
        default=False,
        tracking=True,
        help='If checked, a certificate will be issued upon course completion'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    # Relational fields
    session_ids = fields.One2many(
        comodel_name='training.session',
        inverse_name='course_id',
        string='Sessions'
    )
    session_count = fields.Integer(
        string='Number of Sessions',
        compute='_compute_session_count',
        store=True
    )
    certificate_ids = fields.One2many(
        comodel_name='training.certificate',
        inverse_name='course_id',
        string='Certificates'
    )
    certificate_count = fields.Integer(
        string='Certificates Issued',
        compute='_compute_certificate_count'
    )

    @api.depends('session_ids')
    def _compute_session_count(self):
        for course in self:
            course.session_count = len(course.session_ids)

    @api.depends('certificate_ids')
    def _compute_certificate_count(self):
        for course in self:
            course.certificate_count = len(course.certificate_ids)

    def action_view_sessions(self):
        """Smart button action to view course sessions"""
        self.ensure_one()
        return {
            'name': 'Sessions',
            'type': 'ir.actions.act_window',
            'res_model': 'training.session',
            'view_mode': 'tree,form,calendar',
            'domain': [('course_id', '=', self.id)],
            'context': {'default_course_id': self.id}
        }

    def action_view_certificates(self):
        """Smart button action to view issued certificates"""
        self.ensure_one()
        return {
            'name': 'Certificates',
            'type': 'ir.actions.act_window',
            'res_model': 'training.certificate',
            'view_mode': 'tree,kanban,form',
            'domain': [('course_id', '=', self.id)],
        }