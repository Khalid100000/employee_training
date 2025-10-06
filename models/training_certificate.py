# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _


class TrainingCertificate(models.Model):
    _name = 'training.certificate'
    _description = 'Training Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'issue_date desc'

    name = fields.Char(
        string='Certificate Number',
        default='New',
        readonly=True,
        copy=False,
        index=True
    )
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='restrict',
        tracking=True,
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
    enrollment_id = fields.Many2one(
        comodel_name='training.enrollment',
        string='Related Enrollment',
        ondelete='set null'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    issue_date = fields.Date(
        string='Issue Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    expiry_date = fields.Date(
        string='Expiry Date',
        compute='_compute_expiry_date',
        store=True,
        tracking=True,
        index=True
    )
    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_is_expired',
        store=True
    )
    days_until_expiry = fields.Integer(
        string='Days Until Expiry',
        compute='_compute_days_until_expiry',
        store=True
    )
    state = fields.Selection([
        ('valid', 'Valid'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='Status', compute='_compute_state', store=True, index=True)
    
    # For notifications
    expiry_notified = fields.Boolean(
        string='Expiry Notification Sent',
        default=False,
        help='Whether expiry notification has been sent'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate certificate number"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('training.certificate') or 'New'
        return super().create(vals_list)

    def _compute_access_url(self):
        """Compute portal access URL"""
        super()._compute_access_url()
        for certificate in self:
            certificate.access_url = f'/my/certificates/{certificate.id}'

    @api.depends('issue_date', 'course_id', 'course_id.is_certification')
    def _compute_expiry_date(self):
        """Auto-calculate expiry date (+2 years for certification courses)"""
        for certificate in self:
            if certificate.course_id.is_certification and certificate.issue_date:
                certificate.expiry_date = certificate.issue_date + relativedelta(years=2)
            else:
                certificate.expiry_date = False

    @api.depends('expiry_date')
    def _compute_is_expired(self):
        today = fields.Date.context_today(self)
        for certificate in self:
            certificate.is_expired = (
                certificate.expiry_date and certificate.expiry_date < today
            )

    @api.depends('expiry_date')
    def _compute_days_until_expiry(self):
        today = fields.Date.context_today(self)
        for certificate in self:
            if certificate.expiry_date:
                delta = certificate.expiry_date - today
                certificate.days_until_expiry = delta.days
            else:
                certificate.days_until_expiry = 0

    @api.depends('expiry_date', 'is_expired', 'days_until_expiry')
    def _compute_state(self):
        for certificate in self:
            if not certificate.expiry_date:
                certificate.state = 'valid'
            elif certificate.is_expired:
                certificate.state = 'expired'
            elif certificate.days_until_expiry <= 30:
                certificate.state = 'expiring_soon'
            else:
                certificate.state = 'valid'

    def action_renew_certificate(self):
        """Create a new certificate with updated dates"""
        self.ensure_one()
        new_cert = self.copy({
            'issue_date': fields.Date.context_today(self),
            'expiry_notified': False,
        })
        return {
            'name': _('Renewed Certificate'),
            'type': 'ir.actions.act_window',
            'res_model': 'training.certificate',
            'res_id': new_cert.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def _cron_check_expiring_certificates(self):
        """Cron job to check for expiring certificates and send notifications"""
        today = fields.Date.context_today(self)
        expiry_threshold = today + relativedelta(days=30)
        
        # Find certificates expiring within 30 days that haven't been notified
        expiring_certs = self.search([
            ('expiry_date', '<=', expiry_threshold),
            ('expiry_date', '>=', today),
            ('expiry_notified', '=', False),
        ])
        
        for cert in expiring_certs:
            cert._send_expiry_notification()
            cert.expiry_notified = True
        
        return True

    def _send_expiry_notification(self):
        """Send expiry notification to employee and manager"""
        self.ensure_one()
        
        # Create activity for employee (if has user)
        if self.employee_id.user_id:
            self.activity_schedule(
                'mail.mail_activity_data_warning',
                summary=_('Certificate Expiring Soon'),
                note=_(
                    'Your certificate "%s" for course "%s" will expire on %s. '
                    'Please renew it before expiry.',
                    self.name,
                    self.course_id.name,
                    self.expiry_date
                ),
                user_id=self.employee_id.user_id.id,
            )
        
        # Create activity for manager
        if self.employee_id.parent_id and self.employee_id.parent_id.user_id:
            self.activity_schedule(
                'mail.mail_activity_data_warning',
                summary=_('Team Member Certificate Expiring'),
                note=_(
                    'Certificate "%s" for %s will expire on %s. '
                    'Course: "%s"',
                    self.name,
                    self.employee_id.name,
                    self.expiry_date,
                    self.course_id.name
                ),
                user_id=self.employee_id.parent_id.user_id.id,
            )
        
        # Log in chatter
        self.message_post(
            body=_("Expiry notification sent. Certificate expires on %s", self.expiry_date)
        )

    def action_print_certificate(self):
        """Print certificate PDF"""
        self.ensure_one()
        return self.env.ref('employee_training.action_report_training_certificate').report_action(self)