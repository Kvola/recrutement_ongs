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