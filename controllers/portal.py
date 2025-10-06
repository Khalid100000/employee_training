# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class TrainingPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Add training enrollments and certificates to portal home"""
        values = super()._prepare_home_portal_values(counters)
        employee = request.env.user.employee_id
        
        if 'enrollment_count' in counters:
            values['enrollment_count'] = request.env['training.enrollment'].search_count([
                ('employee_id.user_id', '=', request.env.user.id)
            ])
        
        if 'certificate_count' in counters:
            values['certificate_count'] = request.env['training.certificate'].search_count([
                ('employee_id.user_id', '=', request.env.user.id)
            ])
        
        return values

    @http.route(['/my/enrollments', '/my/enrollments/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_enrollments(self, page=1, sortby=None, **kw):
        """Display user's training enrollments"""
        values = self._prepare_portal_layout_values()
        TrainingEnrollment = request.env['training.enrollment']
        
        domain = [('employee_id.user_id', '=', request.env.user.id)]
        
        # Count for pager
        enrollment_count = TrainingEnrollment.search_count(domain)
        
        # Pager
        pager = portal_pager(
            url="/my/enrollments",
            total=enrollment_count,
            page=page,
            step=self._items_per_page
        )
        
        # Get enrollments
        enrollments = TrainingEnrollment.search(
            domain,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        
        values.update({
            'enrollments': enrollments,
            'page_name': 'enrollment',
            'pager': pager,
            'default_url': '/my/enrollments',
        })
        
        return request.render("employee_training.portal_my_enrollments", values)

    @http.route(['/my/enrollments/<int:enrollment_id>'], type='http', auth="user", website=True)
    def portal_enrollment_detail(self, enrollment_id, **kw):
        """Display enrollment detail"""
        enrollment = request.env['training.enrollment'].browse(enrollment_id)
        
        # Check access
        if enrollment.employee_id.user_id != request.env.user:
            return request.redirect('/my')
        
        values = {
            'enrollment': enrollment,
            'page_name': 'enrollment',
        }
        
        return request.render("employee_training.portal_enrollment_detail", values)

    @http.route(['/my/certificates', '/my/certificates/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_certificates(self, page=1, sortby=None, **kw):
        """Display user's certificates"""
        values = self._prepare_portal_layout_values()
        TrainingCertificate = request.env['training.certificate']
        
        domain = [('employee_id.user_id', '=', request.env.user.id)]
        
        # Count for pager
        certificate_count = TrainingCertificate.search_count(domain)
        
        # Pager
        pager = portal_pager(
            url="/my/certificates",
            total=certificate_count,
            page=page,
            step=self._items_per_page
        )
        
        # Get certificates
        certificates = TrainingCertificate.search(
            domain,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        
        values.update({
            'certificates': certificates,
            'page_name': 'certificate',
            'pager': pager,
            'default_url': '/my/certificates',
        })
        
        return request.render("employee_training.portal_my_certificates", values)

    @http.route(['/my/certificates/<int:certificate_id>'], type='http', auth="user", website=True)
    def portal_certificate_detail(self, certificate_id, **kw):
        """Display certificate detail"""
        certificate = request.env['training.certificate'].browse(certificate_id)
        
        # Check access
        if certificate.employee_id.user_id != request.env.user:
            return request.redirect('/my')
        
        values = {
            'certificate': certificate,
            'page_name': 'certificate',
        }
        
        return request.render("employee_training.portal_certificate_detail", values)

    @http.route(['/my/certificates/<int:certificate_id>/download'], type='http', auth="user", website=True)
    def portal_certificate_download(self, certificate_id, **kw):
        """Download certificate PDF"""
        certificate = request.env['training.certificate'].browse(certificate_id)
        
        # Check access
        if certificate.employee_id.user_id != request.env.user:
            return request.redirect('/my')
        
        # Generate PDF
        pdf, _ = request.env['ir.actions.report']._render_qweb_pdf(
            'employee_training.action_report_training_certificate',
            [certificate_id]
        )
        
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', f'attachment; filename="Certificate-{certificate.name}.pdf"')
        ]
        
        return request.make_response(pdf, headers=pdfhttpheaders)