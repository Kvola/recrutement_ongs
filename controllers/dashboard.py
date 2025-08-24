# controllers/dashboard.py
# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
from datetime import datetime, timedelta

class OngDashboardController(http.Controller):

    @http.route('/ong/dashboard/data', type='json', auth='user', methods=['POST'])
    def get_dashboard_data(self, **kwargs):
        """Retourner les données du tableau de bord"""
        try:
            # Statistiques générales
            campaigns = request.env['ong.recruitment.campaign'].search([])
            applications = request.env['ong.application'].search([])
            
            # Données principales
            stats = {
                'total_campaigns': len(campaigns),
                'active_campaigns': len(campaigns.filtered(lambda c: c.state == 'open')),
                'total_applications': len(applications),
                'selected_ongs': len(applications.filtered(lambda a: a.state == 'selected')),
                'pending_applications': len(applications.filtered(lambda a: a.state in ['submitted', 'under_review'])),
                'rejected_applications': len(applications.filtered(lambda a: a.state == 'rejected')),
            }
            
            # Données pour les graphiques
            charts_data = self._get_charts_data()
            
            # Campagnes récentes
            recent_campaigns = campaigns.sorted('create_date', reverse=True)[:5]
            campaigns_data = []
            for campaign in recent_campaigns:
                campaigns_data.append({
                    'id': campaign.id,
                    'name': campaign.name,
                    'state': campaign.state,
                    'state_label': dict(campaign._fields['state'].selection)[campaign.state],
                    'total_applications': campaign.total_applications,
                    'selected_applications': campaign.selected_applications,
                    'start_date': campaign.start_date.strftime('%d/%m/%Y') if campaign.start_date else '',
                    'end_date': campaign.end_date.strftime('%d/%m/%Y') if campaign.end_date else '',
                })
            
            # Applications récentes
            recent_applications = applications.sorted('create_date', reverse=True)[:10]
            applications_data = []
            for app in recent_applications:
                applications_data.append({
                    'id': app.id,
                    'name': app.name,
                    'state': app.state,
                    'state_label': dict(app._fields['state'].selection)[app.state],
                    'total_score': app.total_score,
                    'campaign_name': app.campaign_id.name,
                    'submission_date': app.submission_date.strftime('%d/%m/%Y %H:%M') if app.submission_date else '',
                    'country': app.country_id.name if app.country_id else '',
                })
            
            return {
                'stats': stats,
                'charts': charts_data,
                'recent_campaigns': campaigns_data,
                'recent_applications': applications_data,
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_charts_data(self):
        """Préparer les données pour les graphiques"""
        applications = request.env['ong.application'].search([])
        
        # Graphique par état des candidatures
        states_data = {}
        for app in applications:
            state_label = dict(app._fields['state'].selection)[app.state]
            states_data[state_label] = states_data.get(state_label, 0) + 1
        
        # Graphique par pays
        countries_data = {}
        for app in applications:
            country = app.country_id.name if app.country_id else 'Non spécifié'
            countries_data[country] = countries_data.get(country, 0) + 1
        
        # Top 5 des pays
        top_countries = sorted(countries_data.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Évolution mensuelle des candidatures
        monthly_data = self._get_monthly_applications_data()
        
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
        
        # Domaines d'activité les plus populaires
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
            'monthly_applications': monthly_data,
            'score_distribution': {
                'labels': list(score_ranges.keys()),
                'data': list(score_ranges.values())
            },
            'top_activity_domains': {
                'labels': [item[0] for item in top_domains],
                'data': [item[1] for item in top_domains]
            }
        }
    
    def _get_monthly_applications_data(self):
        """Données d'évolution mensuelle des candidatures"""
        # Derniers 12 mois
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        monthly_data = {}
        current = start_date
        
        while current <= end_date:
            month_key = current.strftime('%Y-%m')
            month_label = current.strftime('%m/%Y')
            monthly_data[month_label] = 0
            current += timedelta(days=32)
            current = current.replace(day=1)  # Premier du mois suivant
        
        # Compter les candidatures par mois
        applications = request.env['ong.application'].search([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date)
        ])
        
        for app in applications:
            month_label = app.create_date.strftime('%m/%Y')
            if month_label in monthly_data:
                monthly_data[month_label] += 1
        
        return {
            'labels': list(monthly_data.keys()),
            'data': list(monthly_data.values())
        }

    @http.route('/ong/dashboard/export/<string:format>', type='http', auth='user')
    def export_dashboard(self, format='pdf', **kwargs):
        """Exporter les données du tableau de bord"""
        if format == 'excel':
            return self._export_excel_dashboard()
        elif format == 'pdf':
            return self._export_pdf_dashboard()
        else:
            return request.not_found()
    
    def _export_excel_dashboard(self):
        """Exporter le tableau de bord en Excel"""
        try:
            report = request.env['ong.dashboard.report']
            return report.generate_excel_dashboard()
        except Exception as e:
            return request.make_response(
                f'Erreur lors de la génération du rapport Excel: {str(e)}',
                headers=[('Content-Type', 'text/plain')]
            )
    
    def _export_pdf_dashboard(self):
        """Exporter le tableau de bord en PDF"""
        try:
            report = request.env['ong.dashboard.report']
            return report.generate_pdf_dashboard()
        except Exception as e:
            return request.make_response(
                f'Erreur lors de la génération du rapport PDF: {str(e)}',
                headers=[('Content-Type', 'text/plain')]
            )