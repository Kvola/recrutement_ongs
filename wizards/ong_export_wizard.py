# wizards/ong_export_wizard.py - VERSION CORRIGÉE POUR RÉSOUDRE L'ERREUR PDF
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import xlsxwriter
import io
import base64
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class OngExportWizard(models.TransientModel):
    _name = 'ong.export.wizard'
    _description = 'Assistant d\'Export des Données ONGs'

    export_type = fields.Selection([
        ('dashboard', 'Tableau de Bord'),
        ('campaigns', 'Campagnes'),
        ('applications', 'Candidatures'),
        ('evaluations', 'Évaluations Détaillées'),
        ('statistics', 'Statistiques Complètes')
    ], string='Type d\'Export', required=True, default='applications')
    
    date_from = fields.Date('Date de Début')
    date_to = fields.Date('Date de Fin', default=fields.Date.today)
    
    campaign_ids = fields.Many2many('ong.recruitment.campaign', string='Campagnes Spécifiques')
    include_scores = fields.Boolean('Inclure les Scores', default=True)
    include_evaluations = fields.Boolean('Inclure les Évaluations Détaillées', default=False)
    include_documents = fields.Boolean('Inclure Infos Documents', default=True)
    format_type = fields.Selection([
        ('xlsx', 'Excel (.xlsx)'),
        ('pdf', 'PDF')
    ], string='Format', default='xlsx')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError("La date de début doit être antérieure à la date de fin")

    def action_export(self):
        """Action principale d'export selon le format choisi"""
        try:
            if self.format_type == 'xlsx':
                return self.export_excel()
            elif self.format_type == 'pdf':
                return self.export_pdf()
        except Exception as e:
            _logger.error(f"Erreur lors de l'export: {str(e)}")
            raise ValidationError(f"Erreur lors de l'export: {str(e)}")

    def export_excel(self):
        """Exporter en format Excel"""
        try:
            if self.export_type == 'dashboard':
                return self._export_dashboard_excel()
            elif self.export_type == 'campaigns':
                return self._export_campaigns_excel()
            elif self.export_type == 'applications':
                return self._export_applications_excel()
            elif self.export_type == 'evaluations':
                return self._export_evaluations_excel()
            elif self.export_type == 'statistics':
                return self._export_statistics_excel()
        except Exception as e:
            _logger.error(f"Erreur lors de l'export Excel: {str(e)}")
            raise ValidationError(f"Erreur lors de l'export: {str(e)}")

    def export_pdf(self):
        """Exporter en format PDF - VERSION ENTIÈREMENT CORRIGÉE"""
        try:
            # Pour le PDF, on utilise toujours la génération simple sans templates
            if self.export_type == 'applications':
                return self._generate_simple_applications_pdf()
            elif self.export_type == 'campaigns':
                return self._generate_simple_campaigns_pdf()
            elif self.export_type == 'dashboard':
                return self._generate_simple_dashboard_pdf()
            else:
                # Pour les autres types, proposer l'Excel
                raise ValidationError(f"L'export PDF pour '{self.export_type}' n'est pas encore disponible. Veuillez utiliser l'export Excel.")
        except Exception as e:
            _logger.error(f"Erreur lors de l'export PDF: {str(e)}")
            raise ValidationError(f"Erreur lors de l'export PDF: {str(e)}")

    def _generate_simple_applications_pdf(self):
        """Générer un PDF simple pour les candidatures sans dépendance aux templates"""
        try:
            # Essayer d'importer reportlab
            try:
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import A4, landscape
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
            except ImportError:
                raise ValidationError(
                    "La génération de PDF nécessite la bibliothèque ReportLab. "
                    "Veuillez installer ReportLab (pip install reportlab) ou utiliser l'export Excel."
                )

            # Récupérer les applications
            applications = self.env['ong.application'].search(self._get_applications_domain())
            
            if not applications:
                raise ValidationError("Aucune candidature trouvée avec les critères sélectionnés")

            # Créer le buffer
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.darkblue,
                alignment=1,  # Center
                spaceAfter=20
            )
            
            # Contenu
            story = []
            
            # Titre
            story.append(Paragraph("RAPPORT DES CANDIDATURES ONG", title_style))
            story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Statistiques
            total_apps = len(applications)
            selected_apps = len(applications.filtered(lambda a: a.state == 'selected'))
            rejected_apps = len(applications.filtered(lambda a: a.state == 'rejected'))
            pending_apps = total_apps - selected_apps - rejected_apps
            avg_score = sum(applications.mapped('total_score')) / total_apps if total_apps > 0 else 0
            
            stats_data = [
                ['Statistiques Générales', ''],
                ['Total candidatures', str(total_apps)],
                ['Candidatures sélectionnées', str(selected_apps)],
                ['Candidatures rejetées', str(rejected_apps)],
                ['En attente', str(pending_apps)],
                ['Score moyen', f'{avg_score:.2f}'],
            ]
            
            stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(stats_table)
            story.append(Spacer(1, 30))
            
            # Tableau des candidatures
            story.append(Paragraph("LISTE DES CANDIDATURES", styles['Heading2']))
            story.append(Spacer(1, 10))
            
            # Headers
            headers = ['Nom ONG', 'Email', 'Pays', 'Exp.(ans)', 'Budget', 'Score', 'État']
            
            # Données
            data = [headers]
            for app in applications.sorted('total_score', reverse=True):
                row = [
                    (app.name or '')[:25] + ('...' if len(app.name or '') > 25 else ''),  # Limiter la longueur
                    (app.email or '')[:25] + ('...' if len(app.email or '') > 25 else ''),
                    app.country_id.name if app.country_id else '',
                    str(app.years_experience or 0),
                    f'{app.annual_budget:,.0f}' if app.annual_budget else '0',
                    f'{app.total_score:.1f}',
                    dict(app._fields['state'].selection).get(app.state, '')
                ]
                data.append(row)
            
            # Créer le tableau
            table = Table(data)
            table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Data
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            story.append(table)
            
            # Générer le PDF
            doc.build(story)
            
            # Créer l'attachment
            filename = f'candidatures_ongs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(buffer.getvalue()),
                'store_fname': filename,
                'mimetype': 'application/pdf'
            })
            
            buffer.close()
            
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
            
        except Exception as e:
            _logger.error(f"Erreur lors de la génération du PDF: {str(e)}")
            raise ValidationError(f"Erreur lors de la génération du PDF: {str(e)}")

    def _generate_simple_campaigns_pdf(self):
        """Générer un PDF simple pour les campagnes"""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
        except ImportError:
            raise ValidationError("ReportLab non installé. Utilisez l'export Excel.")

        # Récupérer les campagnes
        domain = []
        if self.campaign_ids:
            domain.append(('id', 'in', self.campaign_ids.ids))
        campaigns = self.env['ong.recruitment.campaign'].search(domain)
        
        if not campaigns:
            raise ValidationError("Aucune campagne trouvée")

        # Créer le PDF (structure similaire mais adaptée aux campagnes)
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        styles = getSampleStyleSheet()
        story = []
        
        story.append(Paragraph("RAPPORT DES CAMPAGNES", styles['Title']))
        story.append(Spacer(1, 20))
        
        # Tableau des campagnes
        headers = ['Nom Campagne', 'État', 'Date Début', 'Date Fin', 'Candidatures', 'Sélectionnées']
        data = [headers]
        
        for campaign in campaigns:
            row = [
                campaign.name[:30] + ('...' if len(campaign.name) > 30 else ''),
                dict(campaign._fields['state'].selection).get(campaign.state, ''),
                campaign.start_date.strftime('%d/%m/%Y') if campaign.start_date else '',
                campaign.end_date.strftime('%d/%m/%Y') if campaign.end_date else '',
                str(len(campaign.application_ids)),
                str(len(campaign.application_ids.filtered(lambda a: a.state == 'selected')))
            ]
            data.append(row)
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        doc.build(story)
        
        # Créer l'attachment
        filename = f'campagnes_ongs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(buffer.getvalue()),
            'store_fname': filename,
            'mimetype': 'application/pdf'
        })
        
        buffer.close()
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _generate_simple_dashboard_pdf(self):
        """Générer un PDF simple pour le dashboard"""
        raise ValidationError("Export PDF du dashboard non disponible. Utilisez l'export Excel qui contient plus de détails.")

    # === MÉTHODES EXCEL (inchangées) ===
    
    def _export_applications_excel(self):
        """Export détaillé des candidatures en Excel"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Styles
        header_format = workbook.add_format({
            'bold': True, 'font_size': 12, 'align': 'center',
            'bg_color': '#4F81BD', 'font_color': 'white', 'border': 1
        })
        
        cell_format = workbook.add_format({'border': 1, 'align': 'left'})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        date_format = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})
        
        # Récupérer les données
        domain = self._get_applications_domain()
        applications = self.env['ong.application'].search(domain, order='total_score desc')
        
        if not applications:
            raise ValidationError("Aucune candidature trouvée avec les critères sélectionnés")
        
        # Feuille principale
        worksheet = workbook.add_worksheet('Candidatures')
        
        # Headers
        headers = [
            'ID', 'Nom ONG', 'Email', 'Téléphone', 'Site Web',
            'Adresse', 'Ville', 'Pays', 'N° Enregistrement', 'Statut Légal',
            'Activités Principales', 'Domaines d\'Activité', 'Budget Annuel (CFA)',
            'Nb Employés', 'Nb Bénévoles', 'Années Expérience',
            'Sources Financement', 'Projets Précédents', 'Références',
            'Campagne', 'État', 'Date Soumission'
        ]
        
        if self.include_scores:
            headers.extend(['Score Total', 'Score Expérience', 'Score Budget', 
                          'Score Équipe', 'Score Documents', 'Score Complétude'])
        
        if self.include_documents:
            headers.extend(['Statuts Fournis', 'Certificat Fourni', 'Rapport Financier Fourni'])
        
        # Écrire les headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Données
        for row, app in enumerate(applications, 1):
            col = 0
            
            # Informations de base
            data = [
                app.id, app.name, app.email or '', app.phone or '', app.website or '',
                app.street or '', app.city or '', 
                app.country_id.name if app.country_id else '',
                app.registration_number or '',
                dict(app._fields['legal_status'].selection).get(app.legal_status, ''),
                app.main_activities or '',
                ', '.join([d.name for d in app.activity_domains]),
                app.annual_budget or 0,
                app.staff_count or 0, app.volunteer_count or 0, app.years_experience or 0,
                app.funding_sources or '', app.previous_projects or '', app.references or '',
                app.campaign_id.name if app.campaign_id else '',
                dict(app._fields['state'].selection).get(app.state, ''),
                app.submission_date
            ]
            
            # Écrire les données de base
            for i, value in enumerate(data):
                if i in [12]:  # Budget
                    worksheet.write(row, col + i, value, number_format)
                elif i in [21]:  # Date
                    worksheet.write(row, col + i, value, date_format)
                else:
                    worksheet.write(row, col + i, value, cell_format)
            
            col += len(data)
            
            # Scores si demandés
            if self.include_scores:
                scores = self._get_application_scores(app)
                for score in scores.values():
                    worksheet.write(row, col, score, number_format)
                    col += 1
            
            # Documents si demandés
            if self.include_documents:
                docs = [
                    'Oui' if app.statute_document else 'Non',
                    'Oui' if app.certificate_document else 'Non',
                    'Oui' if app.financial_report else 'Non'
                ]
                for doc in docs:
                    worksheet.write(row, col, doc, cell_format)
                    col += 1
        
        # Ajuster les colonnes
        worksheet.set_column('A:Z', 15)
        worksheet.set_column('B:B', 25)  # Nom ONG plus large
        worksheet.set_column('C:C', 25)  # Email plus large
        
        # Feuille de résumé
        self._add_summary_sheet(workbook, applications)
        
        workbook.close()
        output.seek(0)
        
        # Créer l'attachment
        filename = f'candidatures_ongs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue()),
            'store_fname': filename,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        output.close()
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _export_campaigns_excel(self):
        """Export des campagnes en Excel"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Récupérer les données
        domain = []
        if self.campaign_ids:
            domain.append(('id', 'in', self.campaign_ids.ids))
        campaigns = self.env['ong.recruitment.campaign'].search(domain)
        
        if not campaigns:
            raise ValidationError("Aucune campagne trouvée")
        
        # Styles
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#4F81BD', 'font_color': 'white', 'border': 1
        })
        cell_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy hh:mm'})
        
        # Feuille principale
        worksheet = workbook.add_worksheet('Campagnes')
        
        headers = ['ID', 'Nom', 'Description', 'Date Début', 'Date Fin', 'Max Sélections', 
                  'État', 'Total Candidatures', 'Sélectionnées', 'Rejetées']
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        for row, campaign in enumerate(campaigns, 1):
            data = [
                campaign.id,
                campaign.name,
                campaign.get_description_preview(100) if hasattr(campaign, 'get_description_preview') else '',
                campaign.start_date,
                campaign.end_date,
                campaign.max_selections,
                dict(campaign._fields['state'].selection).get(campaign.state, ''),
                len(campaign.application_ids),
                len(campaign.application_ids.filtered(lambda a: a.state == 'selected')),
                len(campaign.application_ids.filtered(lambda a: a.state == 'rejected'))
            ]
            
            for col, value in enumerate(data):
                if col in [3, 4]:  # Dates
                    worksheet.write(row, col, value, date_format)
                else:
                    worksheet.write(row, col, value, cell_format)
        
        worksheet.set_column('A:Z', 15)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 50)
        
        workbook.close()
        output.seek(0)
        
        filename = f'campagnes_ongs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue()),
            'store_fname': filename,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        output.close()
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _export_dashboard_excel(self):
        """Export du dashboard en Excel"""
        raise ValidationError("Export dashboard Excel non encore implémenté")

    def _export_evaluations_excel(self):
        """Export des évaluations en Excel"""
        raise ValidationError("Export évaluations Excel non encore implémenté")

    def _export_statistics_excel(self):
        """Export des statistiques en Excel"""
        raise ValidationError("Export statistiques Excel non encore implémenté")
    
    def _get_applications_domain(self):
        """Construire le domaine pour filtrer les candidatures"""
        domain = []
        
        if self.campaign_ids:
            domain.append(('campaign_id', 'in', self.campaign_ids.ids))
        
        if self.date_from:
            domain.append(('create_date', '>=', self.date_from))
        
        if self.date_to:
            domain.append(('create_date', '<=', self.date_to))
        
        # Utiliser les IDs du contexte si disponibles (sélection multiple)
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            domain.append(('id', 'in', active_ids))
        
        return domain

    def _get_application_scores(self, application):
        """Récupérer tous les scores d'une candidature"""
        scores = {
            'total': application.total_score,
            'experience': 0,
            'budget': 0,
            'staff': 0,
            'documents': 0,
            'completeness': 0
        }
        
        for evaluation in application.evaluation_ids:
            criterion_code = evaluation.criterion_id.code
            if criterion_code in scores:
                scores[criterion_code] = evaluation.score
        
        return scores

    def _add_summary_sheet(self, workbook, applications):
        """Ajouter une feuille de résumé"""
        worksheet = workbook.add_worksheet('Résumé')
        
        header_format = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center',
            'bg_color': '#4F81BD', 'font_color': 'white'
        })
        
        cell_format = workbook.add_format({'border': 1})
        
        worksheet.merge_range('A1:B1', 'RÉSUMÉ DES CANDIDATURES', header_format)
        
        # Statistiques
        stats = [
            ('Total candidatures', len(applications)),
            ('Candidatures sélectionnées', len(applications.filtered(lambda a: a.state == 'selected'))),
            ('Candidatures rejetées', len(applications.filtered(lambda a: a.state == 'rejected'))),
            ('En attente', len(applications.filtered(lambda a: a.state in ['submitted', 'under_review']))),
            ('Score moyen', sum(applications.mapped('total_score')) / len(applications) if applications else 0),
            ('Score maximum', max(applications.mapped('total_score')) if applications else 0),
        ]
        
        for i, (label, value) in enumerate(stats, 3):
            worksheet.write(i, 0, label, cell_format)
            if isinstance(value, float):
                worksheet.write(i, 1, f'{value:.2f}', cell_format)
            else:
                worksheet.write(i, 1, value, cell_format)