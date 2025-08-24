# models/ong_reports.py
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.http import request
import xlsxwriter
import io
import base64
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class OngDashboardReport(models.TransientModel):
    _name = 'ong.dashboard.report'
    _description = 'Générateur de Rapports Dashboard'

    def generate_excel_dashboard(self):
        """Générer un rapport Excel du tableau de bord"""
        try:
            # Créer un buffer pour le fichier Excel
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            
            # Styles
            header_format = workbook.add_format({
                'bold': True,
                'font_size': 14,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#4F81BD',
                'font_color': 'white',
                'border': 1
            })
            
            subheader_format = workbook.add_format({
                'bold': True,
                'font_size': 12,
                'align': 'center',
                'bg_color': '#B8CCE4',
                'border': 1
            })
            
            cell_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            
            number_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'num_format': '#,##0'
            })
            
            # Récupérer les données
            data = self._get_dashboard_data()
            
            # Feuille 1: Vue d'ensemble
            self._create_overview_sheet(workbook, data, header_format, subheader_format, cell_format, number_format)
            
            # Feuille 2: Campagnes
            self._create_campaigns_sheet(workbook, header_format, subheader_format, cell_format)
            
            # Feuille 3: Candidatures
            self._create_applications_sheet(workbook, header_format, subheader_format, cell_format, number_format)
            
            # Feuille 4: Statistiques détaillées
            self._create_statistics_sheet(workbook, data, header_format, subheader_format, cell_format, number_format)
            
            workbook.close()
            output.seek(0)
            
            # Préparer la réponse HTTP
            filename = f'dashboard_ongs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            
            response = request.make_response(
                output.getvalue(),
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename="{filename}"')
                ]
            )
            
            output.close()
            return response
            
        except Exception as e:
            _logger.error(f"Erreur lors de la génération du rapport Excel: {str(e)}")
            raise

    def _create_overview_sheet(self, workbook, data, header_format, subheader_format, cell_format, number_format):
        """Créer la feuille vue d'ensemble"""
        worksheet = workbook.add_worksheet('Vue d\'ensemble')
        
        # Titre
        worksheet.merge_range('A1:F1', 'TABLEAU DE BORD - RECRUTEMENT ONGs', header_format)
        worksheet.merge_range('A2:F2', f'Généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")}', subheader_format)
        
        # KPIs principaux
        row = 4
        worksheet.write(row, 0, 'INDICATEURS CLÉS', subheader_format)
        row += 2
        
        kpis = [
            ('Total Campagnes', data['stats']['total_campaigns']),
            ('Campagnes Actives', data['stats']['active_campaigns']),
            ('Total Candidatures', data['stats']['total_applications']),
            ('ONGs Sélectionnées', data['stats']['selected_ongs']),
            ('Candidatures en Attente', data['stats']['pending_applications']),
            ('Candidatures Rejetées', data['stats']['rejected_applications']),
        ]
        
        for kpi_name, kpi_value in kpis:
            worksheet.write(row, 0, kpi_name, cell_format)
            worksheet.write(row, 1, kpi_value, number_format)
            row += 1
        
        # Taux de sélection
        row += 1
        total_apps = data['stats']['total_applications']
        selection_rate = (data['stats']['selected_ongs'] / total_apps * 100) if total_apps > 0 else 0
        
        worksheet.write(row, 0, 'Taux de Sélection (%)', cell_format)
        worksheet.write(row, 1, f'{selection_rate:.1f}%', cell_format)
        
        # Graphiques data
        row += 3
        worksheet.write(row, 0, 'RÉPARTITION PAR ÉTAT', subheader_format)
        row += 1
        
        worksheet.write(row, 0, 'État', subheader_format)
        worksheet.write(row, 1, 'Nombre', subheader_format)
        row += 1
        
        states_data = data['charts']['applications_by_state']
        for i, (label, value) in enumerate(zip(states_data['labels'], states_data['data'])):
            worksheet.write(row + i, 0, label, cell_format)
            worksheet.write(row + i, 1, value, number_format)
        
        # Ajuster la largeur des colonnes
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 15)

    def _create_campaigns_sheet(self, workbook, header_format, subheader_format, cell_format):
        """Créer la feuille campagnes"""
        worksheet = workbook.add_worksheet('Campagnes')
        
        # Titre
        worksheet.merge_range('A1:H1', 'CAMPAGNES DE RECRUTEMENT', header_format)
        
        # Headers
        headers = [
            'Nom', 'État', 'Date Début', 'Date Fin', 
            'Total Candidatures', 'Sélectionnées', 'Max Sélections', 'Taux Remplissage'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(2, col, header, subheader_format)
        
        # Données
        campaigns = self.env['ong.recruitment.campaign'].search([])
        row = 3
        
        for campaign in campaigns:
            fill_rate = (campaign.selected_applications / campaign.max_selections * 100) if campaign.max_selections > 0 else 0
            
            data_row = [
                campaign.name,
                dict(campaign._fields['state'].selection)[campaign.state],
                campaign.start_date.strftime('%d/%m/%Y') if campaign.start_date else '',
                campaign.end_date.strftime('%d/%m/%Y') if campaign.end_date else '',
                campaign.total_applications,
                campaign.selected_applications,
                campaign.max_selections,
                f'{fill_rate:.1f}%'
            ]
            
            for col, value in enumerate(data_row):
                worksheet.write(row, col, value, cell_format)
            row += 1
        
        # Ajuster les colonnes
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:H', 15)

    def _create_applications_sheet(self, workbook, header_format, subheader_format, cell_format, number_format):
        """Créer la feuille candidatures"""
        worksheet = workbook.add_worksheet('Candidatures')
        
        # Titre
        worksheet.merge_range('A1:J1', 'CANDIDATURES ONGs', header_format)
        
        # Headers
        headers = [
            'Nom ONG', 'Email', 'Pays', 'Statut Légal', 'Campagne', 
            'État', 'Score Total', 'Années Exp.', 'Budget Annuel', 'Date Soumission'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(2, col, header, subheader_format)
        
        # Données
        applications = self.env['ong.application'].search([], order='total_score desc')
        row = 3
        
        for app in applications:
            data_row = [
                app.name,
                app.email,
                app.country_id.name if app.country_id else '',
                dict(app._fields['legal_status'].selection)[app.legal_status] if app.legal_status else '',
                app.campaign_id.name,
                dict(app._fields['state'].selection)[app.state],
                app.total_score,
                app.years_experience,
                app.annual_budget,
                app.submission_date.strftime('%d/%m/%Y %H:%M') if app.submission_date else ''
            ]
            
            for col, value in enumerate(data_row):
                if col in [6, 7, 8]:  # Colonnes numériques
                    worksheet.write(row, col, value, number_format)
                else:
                    worksheet.write(row, col, value, cell_format)
            row += 1
        
        # Ajuster les colonnes
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:J', 15)

    def _create_statistics_sheet(self, workbook, data, header_format, subheader_format, cell_format, number_format):
        """Créer la feuille statistiques détaillées"""
        worksheet = workbook.add_worksheet('Statistiques')
        
        # Titre
        worksheet.merge_range('A1:D1', 'STATISTIQUES DÉTAILLÉES', header_format)
        
        row = 3
        
        # Top pays
        worksheet.write(row, 0, 'TOP 5 PAYS', subheader_format)
        worksheet.write(row + 1, 0, 'Pays', subheader_format)
        worksheet.write(row + 1, 1, 'Candidatures', subheader_format)
        
        countries_data = data['charts']['applications_by_country']
        for i, (country, count) in enumerate(zip(countries_data['labels'], countries_data['data'])):
            worksheet.write(row + 2 + i, 0, country, cell_format)
            worksheet.write(row + 2 + i, 1, count, number_format)
        
        # Distribution des scores
        row += 10
        worksheet.write(row, 0, 'DISTRIBUTION DES SCORES', subheader_format)
        worksheet.write(row + 1, 0, 'Plage', subheader_format)
        worksheet.write(row + 1, 1, 'Nombre', subheader_format)
        
        score_data = data['charts']['score_distribution']
        for i, (range_label, count) in enumerate(zip(score_data['labels'], score_data['data'])):
            worksheet.write(row + 2 + i, 0, range_label, cell_format)
            worksheet.write(row + 2 + i, 1, count, number_format)
        
        # Domaines d'activité
        row += 15
        worksheet.write(row, 0, 'DOMAINES D\'ACTIVITÉ POPULAIRES', subheader_format)
        worksheet.write(row + 1, 0, 'Domaine', subheader_format)
        worksheet.write(row + 1, 1, 'Candidatures', subheader_format)
        
        domains_data = data['charts']['top_activity_domains']
        for i, (domain, count) in enumerate(zip(domains_data['labels'], domains_data['data'])):
            worksheet.write(row + 2 + i, 0, domain, cell_format)
            worksheet.write(row + 2 + i, 1, count, number_format)
        
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 15)

    def generate_pdf_dashboard(self):
        """Générer un rapport PDF du tableau de bord"""
        try:
            # Utiliser le système de rapports d'Odoo
            data = self._get_dashboard_data()
            
            # Créer un contexte pour le template
            context = {
                'data': data,
                'generate_date': datetime.now().strftime('%d/%m/%Y à %H:%M'),
            }
            
            # Générer le PDF
            pdf = request.env.ref('recrutement_ongs.action_report_dashboard_pdf')._render_qweb_pdf([1], data=context)
            
            filename = f'dashboard_ongs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            
            return request.make_response(
                pdf[0],
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}"')
                ]
            )
            
        except Exception as e:
            _logger.error(f"Erreur lors de la génération du rapport PDF: {str(e)}")
            raise

    def _get_dashboard_data(self):
        """Récupérer toutes les données du dashboard"""
        campaigns = self.env['ong.recruitment.campaign'].search([])
        applications = self.env['ong.application'].search([])
        
        # Statistiques de base
        stats = {
            'total_campaigns': len(campaigns),
            'active_campaigns': len(campaigns.filtered(lambda c: c.state == 'open')),
            'total_applications': len(applications),
            'selected_ongs': len(applications.filtered(lambda a: a.state == 'selected')),
            'pending_applications': len(applications.filtered(lambda a: a.state in ['submitted', 'under_review'])),
            'rejected_applications': len(applications.filtered(lambda a: a.state == 'rejected')),
        }
        
        # Données pour les graphiques
        charts_data = self._get_charts_data(applications)
        
        return {
            'stats': stats,
            'charts': charts_data,
        }
    
    def _get_charts_data(self, applications):
        """Préparer les données pour les graphiques (version simplifiée pour rapports)"""
        # États des candidatures
        states_data = {}
        for app in applications:
            state_label = dict(app._fields['state'].selection)[app.state]
            states_data[state_label] = states_data.get(state_label, 0) + 1
        
        # Pays
        countries_data = {}
        for app in applications:
            country = app.country_id.name if app.country_id else 'Non spécifié'
            countries_data[country] = countries_data.get(country, 0) + 1
        
        top_countries = sorted(countries_data.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Distribution des scores
        score_ranges = {
            '0-20': 0, '21-40': 0, '41-60': 0, 
            '61-80': 0, '81-100': 0, '100+': 0
        }
        
        for app in applications:
            score = app.total_score
            if score <= 20:
                score_ranges['0-20'] += 1
            elif score <= 40:
                score_ranges['21-40'] += 1
            elif score <= 60:
                score_ranges['41-60'] += 1
            elif score <= 80:
                score_ranges['61-80'] += 1
            elif score <= 100:
                score_ranges['81-100'] += 1
            else:
                score_ranges['100+'] += 1
        
        # Domaines d'activité
        domains_data = {}
        for app in applications:
            for domain in app.activity_domains:
                domains_data[domain.name] = domains_data.get(domain.name, 0) + 1
        
        top_domains = sorted(domains_data.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'applications_by_state': {
                'labels': list(states_data.keys()),
                'data': list(states_data.values())
            },
            'applications_by_country': {
                'labels': [item[0] for item in top_countries],
                'data': [item[1] for item in top_countries]
            },
            'score_distribution': {
                'labels': list(score_ranges.keys()),
                'data': list(score_ranges.values())
            },
            'top_activity_domains': {
                'labels': [item[0] for item in top_domains],
                'data': [item[1] for item in top_domains]
            }
        }