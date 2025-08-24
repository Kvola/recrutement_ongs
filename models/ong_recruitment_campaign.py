# models/ong_recruitment_campaign.py
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta
import logging
import html
from markupsafe import Markup
import re

_logger = logging.getLogger(__name__)

class OngRecruitmentCampaign(models.Model):
    _name = 'ong.recruitment.campaign'
    _description = 'Campagne de Recrutement ONG'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Nom de la Campagne', required=True, tracking=True)
    description = fields.Html('Description', sanitize_attributes=True, sanitize_style=True)
    description_text = fields.Text('Description (Texte)', compute='_compute_description_text', store=False)
    start_date = fields.Datetime('Date de Début', required=True, tracking=True)
    end_date = fields.Datetime('Date de Fin', required=True, tracking=True)
    max_selections = fields.Integer('Nombre d\'ONGs à Sélectionner', required=True, default=5)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('open', 'Ouvert aux Candidatures'),
        ('evaluation', 'En Évaluation'),
        ('closed', 'Fermé')
    ], string='État', default='draft', tracking=True)
    
    # Relations
    application_ids = fields.One2many('ong.application', 'campaign_id', string='Candidatures')
    criteria_ids = fields.Many2many('ong.evaluation.criteria', string='Critères d\'Évaluation')
    
    # Compteurs
    total_applications = fields.Integer('Total Candidatures', compute='_compute_statistics')
    selected_applications = fields.Integer('ONGs Sélectionnées', compute='_compute_statistics')
    
    # Configuration
    auto_selection = fields.Boolean('Sélection Automatique', default=True)
    website_published = fields.Boolean('Publié sur le Site Web', default=True)

    @api.depends('description')
    def _compute_description_text(self):
        """Convertit le HTML en texte brut pour l'affichage frontend"""
        for record in self:
            if record.description:
                # Supprimer toutes les balises HTML
                text = re.sub('<.*?>', '', record.description)
                # Décoder les entités HTML
                text = html.unescape(text)
                # Nettoyer les espaces multiples et les sauts de ligne
                text = re.sub(r'\s+', ' ', text).strip()
                record.description_text = text
            else:
                record.description_text = False

    def get_description_preview(self, max_length=150):
        """Retourne un aperçu de la description sans HTML"""
        if not self.description_text:
            return ''
        
        text = self.description_text
        if len(text) <= max_length:
            return text
        
        # Couper au mot le plus proche
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # Si on trouve un espace dans les 20% finaux
            truncated = truncated[:last_space]
        
        return truncated + '...'

    def get_description_safe_html(self):
        """Retourne la description HTML nettoyée pour l'affichage"""
        if not self.description:
            return Markup('')
        
        # Utiliser la sanitisation d'Odoo
        from odoo.tools import html_sanitize
        return Markup(html_sanitize(self.description))
    
    @api.depends('application_ids')
    def _compute_statistics(self):
        for campaign in self:
            campaign.total_applications = len(campaign.application_ids)
            campaign.selected_applications = len(campaign.application_ids.filtered(lambda a: a.state == 'selected'))

    def action_open_campaign(self):
        """Ouvrir la campagne aux candidatures"""
        self.state = 'open'
        self.message_post(body="Campagne ouverte aux candidatures")

    def action_close_applications(self):
        """Fermer les candidatures et passer à l'évaluation"""
        self.state = 'evaluation'
        if self.auto_selection:
            self._auto_select_ongs()

    def action_close_campaign(self):
        """Fermer définitivement la campagne"""
        self.state = 'closed'
        self.message_post(body="Campagne fermée")

    def _auto_select_ongs(self):
        """Sélection automatique des meilleures ONGs"""
        applications = self.application_ids.filtered(lambda a: a.state == 'submitted')
        
        # Calculer les scores pour toutes les candidatures
        for application in applications:
            application._compute_total_score()
        
        # Trier par score décroissant
        sorted_applications = applications.sorted('total_score', reverse=True)
        
        # Sélectionner les meilleures
        selected = sorted_applications[:self.max_selections]
        rejected = sorted_applications[self.max_selections:]
        
        selected.write({'state': 'selected'})
        rejected.write({'state': 'rejected'})
        
        self.message_post(
            body=f"Sélection automatique effectuée: {len(selected)} ONGs sélectionnées sur {len(applications)} candidatures"
        )

    @api.model
    def check_campaign_deadlines(self):
        """Méthode cron pour vérifier les échéances"""
        now = datetime.now()
        
        # Fermer automatiquement les campagnes expirées
        expired_campaigns = self.search([
            ('state', '=', 'open'),
            ('end_date', '<', now)
        ])
        
        for campaign in expired_campaigns:
            campaign.action_close_applications()

    # Ajouter ces méthodes à la classe OngRecruitmentCampaign dans ong_recruitment_campaign.py
    def generate_campaign_excel_report(self):
        """Générer un rapport Excel détaillé pour cette campagne"""
        try:
            import xlsxwriter
            import io
            import base64
            from datetime import datetime
            from odoo.exceptions import ValidationError
            
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            
            # Styles
            title_format = workbook.add_format({
                'bold': True, 'font_size': 16, 'align': 'center',
                'bg_color': '#2E4B7D', 'font_color': 'white', 'border': 1
            })
            
            header_format = workbook.add_format({
                'bold': True, 'font_size': 12, 'align': 'center',
                'bg_color': '#4F81BD', 'font_color': 'white', 'border': 1
            })
            
            subheader_format = workbook.add_format({
                'bold': True, 'font_size': 10, 'align': 'center',
                'bg_color': '#B8CCE4', 'border': 1
            })
            
            cell_format = workbook.add_format({'border': 1, 'align': 'left'})
            number_format = workbook.add_format({'border': 1, 'num_format': '#,##0'})
            decimal_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
            date_format = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy hh:mm'})
            percent_format = workbook.add_format({'border': 1, 'num_format': '0.0%'})
            
            # === Feuille 1: Résumé de la Campagne ===
            ws_summary = workbook.add_worksheet('Résumé Campagne')
            
            # Titre
            ws_summary.merge_range('A1:H1', f'RAPPORT CAMPAGNE: {self.name}', title_format)
            ws_summary.merge_range('A2:H2', f'Généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")}', subheader_format)
            
            # Informations générales
            row = 4
            ws_summary.write(row, 0, 'INFORMATIONS GÉNÉRALES', header_format)
            ws_summary.merge_range(row, 1, row, 3, '', header_format)
            
            info_data = [
                ('Nom de la campagne:', self.name),
                ('État:', dict(self._fields['state'].selection).get(self.state, '')),
                ('Date de début:', self.start_date),
                ('Date de fin:', self.end_date),
                ('Places à pourvoir:', self.max_selections),
                ('Sélection automatique:', 'Oui' if self.auto_selection else 'Non'),
                ('Publié sur le web:', 'Oui' if self.website_published else 'Non'),
            ]
            
            for label, value in info_data:
                row += 1
                ws_summary.write(row, 0, label, cell_format)
                if isinstance(value, datetime):
                    ws_summary.write(row, 1, value, date_format)
                else:
                    ws_summary.write(row, 1, value or '', cell_format)
            
            # Description (nettoyée)
            row += 2
            ws_summary.write(row, 0, 'DESCRIPTION:', header_format)
            ws_summary.merge_range(row, 1, row, 7, '', header_format)
            row += 1
            description_clean = self._clean_html_for_excel(self.description) if self.description else 'Aucune description'
            ws_summary.merge_range(row, 0, row + 2, 7, description_clean, cell_format)
            
            # Statistiques
            row += 4
            ws_summary.write(row, 0, 'STATISTIQUES', header_format)
            ws_summary.merge_range(row, 1, row, 3, '', header_format)
            
            # Calculer les statistiques
            total_apps = len(self.application_ids)
            selected_apps = len(self.application_ids.filtered(lambda a: a.state == 'selected'))
            rejected_apps = len(self.application_ids.filtered(lambda a: a.state == 'rejected'))
            pending_apps = len(self.application_ids.filtered(lambda a: a.state in ['submitted', 'under_review']))
            avg_score = sum(self.application_ids.mapped('total_score')) / total_apps if total_apps > 0 else 0
            completion_rate = (selected_apps / self.max_selections) if self.max_selections > 0 else 0
            
            stats_data = [
                ('Total candidatures:', total_apps),
                ('ONGs sélectionnées:', selected_apps),
                ('ONGs rejetées:', rejected_apps),
                ('En attente:', pending_apps),
                ('Score moyen:', avg_score),
                ('Taux de remplissage:', completion_rate),
            ]
            
            for label, value in stats_data:
                row += 1
                ws_summary.write(row, 0, label, cell_format)
                if label == 'Score moyen:':
                    ws_summary.write(row, 1, value, decimal_format)
                elif label == 'Taux de remplissage:':
                    ws_summary.write(row, 1, value, percent_format)
                else:
                    ws_summary.write(row, 1, value, number_format)
            
            # === Feuille 2: Candidatures Détaillées ===
            ws_apps = workbook.add_worksheet('Candidatures')
            
            # Titre
            ws_apps.merge_range('A1:P1', 'CANDIDATURES DÉTAILLÉES', title_format)
            
            # Headers
            headers = [
                'ID', 'Nom ONG', 'Email', 'Téléphone', 'Pays', 'Ville',
                'Statut Légal', 'Années Exp.', 'Budget Annuel', 'Nb Employés',
                'Score Total', 'État', 'Date Soumission', 'Documents', 'Évaluée', 'Rang'
            ]
            
            for col, header in enumerate(headers):
                ws_apps.write(2, col, header, header_format)
            
            # Trier les candidatures par score décroissant
            applications_sorted = self.application_ids.sorted('total_score', reverse=True)
            
            # Données des candidatures
            for row, app in enumerate(applications_sorted, 3):
                # Calculer le nombre de documents fournis
                docs_count = sum([
                    1 if hasattr(app, 'statute_document') and app.statute_document else 0,
                    1 if hasattr(app, 'certificate_document') and app.certificate_document else 0,
                    1 if hasattr(app, 'financial_report') and app.financial_report else 0,
                ])
                docs_status = f"{docs_count}/3"
                
                # Vérifier si l'ONG a été évaluée
                evaluated = 'Oui' if hasattr(app, 'evaluation_ids') and app.evaluation_ids else 'Non'
                
                # Rang basé sur le score
                rank = row - 2
                
                data = [
                    app.id,
                    app.name or '',
                    app.email or '',
                    app.phone or '',
                    app.country_id.name if app.country_id else '',
                    app.city or '',
                    dict(app._fields['legal_status'].selection).get(app.legal_status, '') if hasattr(app, 'legal_status') else '',
                    getattr(app, 'years_experience', 0) or 0,
                    getattr(app, 'annual_budget', 0) or 0,
                    getattr(app, 'staff_count', 0) or 0,
                    app.total_score or 0,
                    dict(app._fields['state'].selection).get(app.state, ''),
                    getattr(app, 'submission_date', None),
                    docs_status,
                    evaluated,
                    rank
                ]
                
                for col, value in enumerate(data):
                    if col in [7, 9, 15]:  # Entiers
                        ws_apps.write(row, col, value, number_format)
                    elif col in [8]:  # Budget
                        ws_apps.write(row, col, value, decimal_format)
                    elif col in [10]:  # Score
                        ws_apps.write(row, col, value, decimal_format)
                    elif col in [12]:  # Date
                        if value:
                            ws_apps.write(row, col, value, date_format)
                        else:
                            ws_apps.write(row, col, '', cell_format)
                    else:
                        ws_apps.write(row, col, value, cell_format)
            
            # Ajuster la largeur des colonnes
            ws_summary.set_column('A:A', 20)
            ws_summary.set_column('B:B', 25)
            ws_summary.set_column('C:Z', 15)
            
            ws_apps.set_column('A:A', 8)
            ws_apps.set_column('B:B', 25)
            ws_apps.set_column('C:Z', 15)
            
            workbook.close()
            output.seek(0)
            
            # Créer l'attachment
            filename = f'rapport_campagne_{self.name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            filename = filename.replace(' ', '_').replace('/', '_')
            
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
            
        except Exception as e:
            _logger.error(f"Erreur lors de la génération du rapport Excel: {str(e)}")
            from odoo.exceptions import ValidationError
            raise ValidationError(f"Erreur lors de la génération du rapport Excel: {str(e)}")

    def generate_campaign_pdf_report(self):
        """Générer un rapport PDF pour cette campagne"""
        try:
            from odoo.exceptions import ValidationError
            
            # Préparer les données pour le template
            total_apps = len(self.application_ids)
            selected_apps = len(self.application_ids.filtered(lambda a: a.state == 'selected'))
            rejected_apps = len(self.application_ids.filtered(lambda a: a.state == 'rejected'))
            pending_apps = len(self.application_ids.filtered(lambda a: a.state in ['submitted', 'under_review']))
            avg_score = sum(self.application_ids.mapped('total_score')) / total_apps if total_apps > 0 else 0
            
            # Statistiques par pays
            country_stats = {}
            for app in self.application_ids:
                country = app.country_id.name if app.country_id else 'Non spécifié'
                if country not in country_stats:
                    country_stats[country] = {'total': 0, 'selected': 0}
                country_stats[country]['total'] += 1
                if app.state == 'selected':
                    country_stats[country]['selected'] += 1
            
            # Top 5 pays
            top_countries = sorted(country_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:5]
            
            # Répartition par domaines d'activité
            domain_stats = {}
            for app in self.application_ids:
                if hasattr(app, 'activity_domains'):
                    for domain in app.activity_domains:
                        if domain.name not in domain_stats:
                            domain_stats[domain.name] = 0
                        domain_stats[domain.name] += 1
            
            top_domains = sorted(domain_stats.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Distribution des scores
            score_ranges = {
                '0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0
            }
            
            for app in self.application_ids:
                score = app.total_score or 0
                if score <= 20:
                    score_ranges['0-20'] += 1
                elif score <= 40:
                    score_ranges['21-40'] += 1
                elif score <= 60:
                    score_ranges['41-60'] += 1
                elif score <= 80:
                    score_ranges['61-80'] += 1
                else:
                    score_ranges['81-100'] += 1
            
            # Applications triées par score
            top_applications = self.application_ids.sorted('total_score', reverse=True)[:10]
            
            data = {
                'campaign': self,
                'generate_date': datetime.now().strftime('%d/%m/%Y à %H:%M'),
                'stats': {
                    'total_applications': total_apps,
                    'selected_applications': selected_apps,
                    'rejected_applications': rejected_apps,
                    'pending_applications': pending_apps,
                    'average_score': avg_score,
                    'completion_rate': (selected_apps / self.max_selections * 100) if self.max_selections > 0 else 0,
                },
                'top_countries': top_countries,
                'top_domains': top_domains,
                'score_distribution': score_ranges,
                'top_applications': top_applications,
                'description_clean': self._clean_html_for_pdf(self.description) if self.description else 'Aucune description',
            }
            
            # Générer le PDF via le template
            if hasattr(self.env, 'ref'):
                try:
                    report = self.env.ref('recrutement_ongs.action_report_campaign_pdf')
                    return report._render_qweb_pdf([self.id], data=data)
                except:
                    # Fallback si le template n'existe pas
                    _logger.warning("Template PDF non trouvé, retour des données seulement")
                    return data
            else:
                return data
            
        except Exception as e:
            _logger.error(f"Erreur lors de la génération du rapport PDF: {str(e)}")
            from odoo.exceptions import ValidationError
            raise ValidationError(f"Erreur lors de la génération du rapport PDF: {str(e)}")

    def _clean_html_for_excel(self, html_content):
        """Nettoyer le contenu HTML pour l'export Excel"""
        if not html_content:
            return ''
        
        # Vérifier le type de données
        if isinstance(html_content, list):
            html_content = ' '.join(str(item) for item in html_content)
        elif not isinstance(html_content, str):
            html_content = str(html_content)
        
        import re
        import html
        
        # Supprimer les balises HTML
        clean_text = re.sub('<.*?>', '', html_content)
        # Décoder les entités HTML
        clean_text = html.unescape(clean_text)
        # Nettoyer les espaces multiples
        clean_text = ' '.join(clean_text.split())
        # Limiter la longueur
        return clean_text[:1000] + '...' if len(clean_text) > 1000 else clean_text


    def _clean_html_for_pdf(self, html_content):
        """Nettoyer le contenu HTML pour l'export PDF - VERSION CORRIGÉE"""
        if not html_content:
            return ''
        
        # Vérifier et convertir le type de données
        if isinstance(html_content, list):
            # Si c'est une liste, joindre les éléments
            html_content = ' '.join(str(item) for item in html_content)
        elif not isinstance(html_content, str):
            # Si ce n'est pas une string, la convertir
            html_content = str(html_content)
        
        import re
        import html
        
        try:
            # Supprimer les balises HTML
            clean_text = re.sub('<.*?>', '', html_content)
            # Décoder les entités HTML  
            clean_text = html.unescape(clean_text)
            # Nettoyer les espaces multiples et garder les sauts de ligne
            clean_text = re.sub(r' +', ' ', clean_text)
            clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)
            return clean_text.strip()
        except Exception as e:
            _logger.warning(f"Erreur lors du nettoyage HTML: {str(e)}")
            # Retourner le contenu brut en cas d'erreur
            return str(html_content)[:500] + '...' if len(str(html_content)) > 500 else str(html_content)