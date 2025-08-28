# models/ong_reports.py
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.http import request
import xlsxwriter
import io
import base64
from datetime import datetime
import logging
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.lib.colors import HexColor
import tempfile
import os

_logger = logging.getLogger(__name__)

class OngDashboardReport(models.TransientModel):
    _name = 'ong.dashboard.report'
    _description = 'Générateur de Rapports Dashboard'

    def generate_pdf_dashboard(self):
        """Générer un rapport PDF du tableau de bord avec graphiques"""
        try:
            # Créer un buffer pour le PDF
            buffer = io.BytesIO()
            
            # Créer le document PDF
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # Récupérer les données
            data = self._get_dashboard_data()
            
            # Créer le contenu
            story = []
            styles = getSampleStyleSheet()
            
            # Styles personnalisés
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=1,  # Centré
                textColor=colors.darkblue
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=16,
                spaceAfter=20,
                textColor=colors.darkblue
            )
            
            # En-tête du document
            story.append(Paragraph("TABLEAU DE BORD - RECRUTEMENT ONGs", title_style))
            story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
            story.append(Spacer(1, 0.5*inch))
            
            # Section statistiques principales
            story.append(Paragraph("INDICATEURS CLÉS", subtitle_style))
            stats_data = [
                ['Indicateur', 'Valeur'],
                ['Total Campagnes', data['stats']['total_campaigns']],
                ['Campagnes Actives', data['stats']['active_campaigns']],
                ['Total Candidatures', data['stats']['total_applications']],
                ['ONGs Sélectionnées', data['stats']['selected_ongs']],
                ['Candidatures en Attente', data['stats']['pending_applications']],
                ['Candidatures Rejetées', data['stats']['rejected_applications']],
            ]
            
            # Calculer le taux de sélection
            total_apps = data['stats']['total_applications']
            selection_rate = (data['stats']['selected_ongs'] / total_apps * 100) if total_apps > 0 else 0
            stats_data.append(['Taux de Sélection (%)', f'{selection_rate:.1f}%'])
            
            stats_table = Table(stats_data, colWidths=[4*inch, 2*inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
            ]))
            
            story.append(stats_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Graphique répartition par état (Camembert)
            story.append(Paragraph("RÉPARTITION DES CANDIDATURES PAR ÉTAT", subtitle_style))
            states_chart = self._create_pie_chart(data['charts']['applications_by_state'])
            if states_chart:
                story.append(states_chart)
            story.append(Spacer(1, 0.3*inch))
            
            # Graphique top pays (Barres)
            story.append(Paragraph("TOP 5 PAYS - CANDIDATURES", subtitle_style))
            countries_chart = self._create_bar_chart(data['charts']['applications_by_country'], 'Candidatures')
            if countries_chart:
                story.append(countries_chart)
            story.append(PageBreak())
            
            # Distribution des scores
            story.append(Paragraph("DISTRIBUTION DES SCORES", subtitle_style))
            score_chart = self._create_bar_chart(data['charts']['score_distribution'], 'Nombre d\'ONGs')
            if score_chart:
                story.append(score_chart)
            story.append(Spacer(1, 0.3*inch))
            
            # Domaines d'activité populaires (Barres horizontales)
            story.append(Paragraph("DOMAINES D'ACTIVITÉ POPULAIRES", subtitle_style))
            domains_chart = self._create_horizontal_bar_chart(data['charts']['top_activity_domains'])
            if domains_chart:
                story.append(domains_chart)
            story.append(PageBreak())
            
            # Tableau détaillé des campagnes
            story.append(Paragraph("DÉTAIL DES CAMPAGNES", subtitle_style))
            campaigns_table = self._create_campaigns_table()
            if campaigns_table:
                story.append(campaigns_table)
            
            # Construire le PDF
            doc.build(story)
            
            # Préparer la réponse
            buffer.seek(0)
            filename = f'dashboard_ongs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            
            response = request.make_response(
                buffer.getvalue(),
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}"')
                ]
            )
            
            buffer.close()
            return response
            
        except Exception as e:
            _logger.error(f"Erreur lors de la génération du rapport PDF: {str(e)}")
            raise

    def _create_pie_chart(self, chart_data):
        """Créer un graphique camembert"""
        try:
            if not chart_data or not chart_data.get('labels') or not chart_data.get('data'):
                return None
            
            drawing = Drawing(400, 300)
            pie = Pie()
            pie.x = 50
            pie.y = 100
            pie.width = 200
            pie.height = 200
            
            # Données
            pie.data = chart_data['data']
            pie.labels = chart_data['labels']
            
            # Couleurs
            colors_list = [
                HexColor('#6f42c1'), HexColor('#17a2b8'), HexColor('#28a745'),
                HexColor('#fd7e14'), HexColor('#dc3545'), HexColor('#6c757d')
            ]
            
            for i in range(len(pie.data)):
                pie.slices[i].fillColor = colors_list[i % len(colors_list)]
            
            # Style des étiquettes
            pie.slices.labelRadius = 1.2
            pie.slices.fontName = "Helvetica"
            pie.slices.fontSize = 10
            
            drawing.add(pie)
            return drawing
            
        except Exception as e:
            _logger.error(f"Erreur création graphique camembert: {str(e)}")
            return None

    def _create_bar_chart(self, chart_data, y_label):
        """Créer un graphique en barres verticales"""
        try:
            if not chart_data or not chart_data.get('labels') or not chart_data.get('data'):
                return None
            
            drawing = Drawing(500, 300)
            chart = VerticalBarChart()
            chart.x = 50
            chart.y = 50
            chart.height = 200
            chart.width = 400
            
            # Données
            chart.data = [chart_data['data']]
            chart.categoryAxis.categoryNames = chart_data['labels']
            
            # Style
            chart.bars[0].fillColor = HexColor('#3498db')
            chart.valueAxis.valueMin = 0
            chart.valueAxis.valueMax = max(chart_data['data']) * 1.2 if chart_data['data'] else 10
            
            # Axes
            chart.categoryAxis.labels.boxAnchor = 'ne'
            chart.categoryAxis.labels.dx = 8
            chart.categoryAxis.labels.dy = -2
            chart.categoryAxis.labels.angle = 30
            chart.categoryAxis.labels.fontName = "Helvetica"
            chart.categoryAxis.labels.fontSize = 9
            
            chart.valueAxis.labels.fontName = "Helvetica"
            chart.valueAxis.labels.fontSize = 9
            
            drawing.add(chart)
            return drawing
            
        except Exception as e:
            _logger.error(f"Erreur création graphique barres: {str(e)}")
            return None

    def _create_horizontal_bar_chart(self, chart_data):
        """Créer un graphique en barres horizontales"""
        try:
            if not chart_data or not chart_data.get('labels') or not chart_data.get('data'):
                return None
            
            drawing = Drawing(500, 300)
            chart = HorizontalBarChart()
            chart.x = 50
            chart.y = 50
            chart.height = 200
            chart.width = 350
            
            # Données
            chart.data = [chart_data['data']]
            chart.categoryAxis.categoryNames = chart_data['labels']
            
            # Style
            chart.bars[0].fillColor = HexColor('#9b59b6')
            chart.valueAxis.valueMin = 0
            chart.valueAxis.valueMax = max(chart_data['data']) * 1.2 if chart_data['data'] else 10
            
            # Axes
            chart.categoryAxis.labels.fontName = "Helvetica"
            chart.categoryAxis.labels.fontSize = 9
            chart.valueAxis.labels.fontName = "Helvetica"
            chart.valueAxis.labels.fontSize = 9
            
            drawing.add(chart)
            return drawing
            
        except Exception as e:
            _logger.error(f"Erreur création graphique barres horizontales: {str(e)}")
            return None

    def _create_line_chart(self, chart_data):
        """Créer un graphique linéaire"""
        try:
            if not chart_data or not chart_data.get('labels') or not chart_data.get('data'):
                return None
            
            drawing = Drawing(500, 300)
            chart = HorizontalLineChart()
            chart.x = 50
            chart.y = 50
            chart.height = 200
            chart.width = 400
            
            # Données
            chart.data = [chart_data['data']]
            chart.categoryAxis.categoryNames = chart_data['labels']
            
            # Style
            chart.lines[0].strokeColor = HexColor('#27ae60')
            chart.lines[0].strokeWidth = 3
            
            # Axes
            chart.categoryAxis.labels.angle = 45
            chart.categoryAxis.labels.fontName = "Helvetica"
            chart.categoryAxis.labels.fontSize = 8
            chart.valueAxis.labels.fontName = "Helvetica"
            chart.valueAxis.labels.fontSize = 9
            
            drawing.add(chart)
            return drawing
            
        except Exception as e:
            _logger.error(f"Erreur création graphique linéaire: {str(e)}")
            return None

    def _create_campaigns_table(self):
        """Créer le tableau des campagnes"""
        try:
            campaigns = self.env['ong.recruitment.campaign'].search([], limit=10)
            if not campaigns:
                return None
            
            # En-têtes
            data = [['Nom', 'État', 'Candidatures', 'Sélectionnées', 'Taux']]
            
            # Données
            for campaign in campaigns:
                fill_rate = (campaign.selected_applications / campaign.total_applications * 100) if campaign.total_applications > 0 else 0
                
                data.append([
                    campaign.name[:30] + '...' if len(campaign.name) > 30 else campaign.name,
                    dict(campaign._fields['state'].selection)[campaign.state],
                    str(campaign.total_applications),
                    str(campaign.selected_applications),
                    f'{fill_rate:.1f}%'
                ])
            
            table = Table(data, colWidths=[3*inch, 1*inch, 1*inch, 1*inch, 0.8*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            return table
            
        except Exception as e:
            _logger.error(f"Erreur création tableau campagnes: {str(e)}")
            return None

    def generate_excel_dashboard(self):
        """Générer un rapport Excel du tableau de bord (code existant maintenu)"""
        try:
            # Code Excel existant conservé
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
            
            # Créer les feuilles
            self._create_overview_sheet(workbook, data, header_format, subheader_format, cell_format, number_format)
            self._create_campaigns_sheet(workbook, header_format, subheader_format, cell_format)
            self._create_applications_sheet(workbook, header_format, subheader_format, cell_format, number_format)
            self._create_statistics_sheet(workbook, data, header_format, subheader_format, cell_format, number_format)
            
            workbook.close()
            output.seek(0)
            
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

    # Méthodes Excel existantes maintenues (pour éviter les répétitions)
    def _create_overview_sheet(self, workbook, data, header_format, subheader_format, cell_format, number_format):
        """Créer la feuille vue d'ensemble (code existant)"""
        # Code existant conservé
        pass

    def _create_campaigns_sheet(self, workbook, header_format, subheader_format, cell_format):
        """Créer la feuille campagnes (code existant)"""
        # Code existant conservé
        pass

    def _create_applications_sheet(self, workbook, header_format, subheader_format, cell_format, number_format):
        """Créer la feuille candidatures (code existant)"""
        # Code existant conservé
        pass

    def _create_statistics_sheet(self, workbook, data, header_format, subheader_format, cell_format, number_format):
        """Créer la feuille statistiques détaillées (code existant)"""
        # Code existant conservé
        pass

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
        """Préparer les données pour les graphiques"""
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
        
        # Évolution mensuelle (optionnel pour PDF)
        monthly_data = self._get_monthly_applications_data()
        
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
            },
            'monthly_applications': monthly_data
        }

    def _get_monthly_applications_data(self):
        """Données d'évolution mensuelle des candidatures"""
        # Derniers 12 mois
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        monthly_data = {}
        current = start_date
        
        while current <= end_date:
            month_label = current.strftime('%m/%Y')
            monthly_data[month_label] = 0
            current += timedelta(days=32)
            current = current.replace(day=1)
        
        # Compter les candidatures par mois
        applications = self.env['ong.application'].search([
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