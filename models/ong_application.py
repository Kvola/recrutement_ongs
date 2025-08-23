# models/ong_application.py
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)

class OngApplication(models.Model):
    _name = 'ong.application'
    _description = 'Candidature ONG'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'total_score desc, create_date desc'

    # Informations générales
    name = fields.Char('Nom de l\'ONG', required=True, tracking=True)
    email = fields.Char('Email de Contact', required=True)
    phone = fields.Char('Téléphone')
    website = fields.Char('Site Web')
    
    # Adresse
    street = fields.Char('Adresse')
    city = fields.Char('Ville')
    country_id = fields.Many2one('res.country', string='Pays')
    
    # Informations légales
    registration_number = fields.Char('Numéro d\'Enregistrement', required=True)
    legal_status = fields.Selection([
        ('association', 'Association'),
        ('fondation', 'Fondation'),
        ('ong_internationale', 'ONG Internationale'),
        ('autre', 'Autre')
    ], string='Statut Légal', required=True)
    
    # Domaines d'activité
    activity_domains = fields.Many2many('ong.activity.domain', string='Domaines d\'Activité')
    main_activities = fields.Text('Activités Principales', required=True)
    
    # Informations financières
    annual_budget = fields.Float('Budget Annuel (CFA)')
    funding_sources = fields.Text('Sources de Financement')
    
    # Ressources humaines
    staff_count = fields.Integer('Nombre d\'Employés')
    volunteer_count = fields.Integer('Nombre de Bénévoles')
    
    # Expérience et références
    years_experience = fields.Integer('Années d\'Expérience', required=True)
    previous_projects = fields.Text('Projets Précédents')
    references = fields.Text('Références')
    
    # Documents
    statute_document = fields.Binary('Statuts de l\'Organisation')
    statute_document_name = fields.Char('Nom du fichier - Statuts')
    certificate_document = fields.Binary('Certificat d\'Enregistrement')
    certificate_document_name = fields.Char('Nom du fichier - Certificat')
    financial_report = fields.Binary('Rapport Financier')
    financial_report_name = fields.Char('Nom du fichier - Rapport Financier')
    
    # Évaluation
    evaluation_ids = fields.One2many('ong.application.evaluation', 'application_id', string='Évaluations')
    total_score = fields.Float('Score Total', compute='_compute_total_score', store=True)
    
    # Workflow
    campaign_id = fields.Many2one('ong.recruitment.campaign', string='Campagne', required=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumise'),
        ('under_review', 'En Révision'),
        ('selected', 'Sélectionnée'),
        ('rejected', 'Rejetée')
    ], string='État', default='draft', tracking=True)
    
    submission_date = fields.Datetime('Date de Soumission')
    rejection_reason = fields.Text('Motif de Rejet')
    
    # Contraintes et validations
    @api.constrains('email')
    def _check_email(self):
        """Validation de l'adresse email"""
        for record in self:
            if record.email:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, record.email):
                    raise ValidationError("L'adresse email n'est pas valide")
    
    @api.constrains('annual_budget', 'staff_count', 'volunteer_count', 'years_experience')
    def _check_numeric_fields(self):
        """Validation des champs numériques"""
        for record in self:
            if record.annual_budget < 0:
                raise ValidationError("Le budget annuel ne peut pas être négatif")
            if record.staff_count < 0:
                raise ValidationError("Le nombre d'employés ne peut pas être négatif")
            if record.volunteer_count < 0:
                raise ValidationError("Le nombre de bénévoles ne peut pas être négatif")
            if record.years_experience < 0:
                raise ValidationError("Les années d'expérience ne peuvent pas être négatives")
    
    @api.constrains('website')
    def _check_website(self):
        """Validation de l'URL du site web"""
        for record in self:
            if record.website:
                # Ajouter http:// si pas de protocole
                if not record.website.startswith(('http://', 'https://')):
                    record.website = 'http://' + record.website
                
                # Validation basique de l'URL
                url_pattern = r'^https?:\/\/[^\s/$.?#].[^\s]*$'
                if not re.match(url_pattern, record.website):
                    raise ValidationError("L'URL du site web n'est pas valide")

    @api.depends('evaluation_ids.score')
    def _compute_total_score(self):
        """Calcul du score total"""
        for application in self:
            if application.evaluation_ids:
                application.total_score = sum(application.evaluation_ids.mapped('score'))
            else:
                application.total_score = 0.0

    def action_submit(self):
        """Soumettre la candidature"""
        for record in self:
            # Vérifier que la campagne est toujours ouverte
            if record.campaign_id.state != 'open':
                raise ValidationError("Cette campagne n'est plus ouverte aux candidatures")
            
            if record.campaign_id.end_date < fields.Datetime.now():
                raise ValidationError("La date limite de candidature est dépassée")
            
            # Validation des données
            record._validate_application()
            
            # Changement d'état
            record.write({
                'state': 'submitted',
                'submission_date': fields.Datetime.now()
            })
            
            # Évaluation automatique
            record._auto_evaluate()
            
            # Notification
            record._send_submission_notification()
            
            _logger.info(f"Candidature soumise: {record.name} (ID: {record.id})")

    def _validate_application(self):
        """Validation complète de la candidature"""
        for record in self:
            errors = []
            
            # Vérification des champs obligatoires
            required_fields = {
                'name': 'Nom de l\'organisation',
                'email': 'Email',
                'registration_number': 'Numéro d\'enregistrement',
                'legal_status': 'Statut légal',
                'main_activities': 'Activités principales',
                'years_experience': 'Années d\'expérience'
            }
            
            for field, label in required_fields.items():
                value = getattr(record, field)
                if not value or (isinstance(value, str) and value.strip() == ''):
                    errors.append(f"Le champ '{label}' est obligatoire")
            
            # Vérification que l'expérience est positive
            if record.years_experience <= 0:
                errors.append("Les années d'expérience doivent être supérieures à 0")
            
            # Vérification qu'au moins un domaine d'activité est sélectionné
            if not record.activity_domains:
                errors.append("Au moins un domaine d'activité doit être sélectionné")
            
            if errors:
                raise ValidationError('\n'.join(errors))

    def _auto_evaluate(self):
        """Évaluation automatique selon les critères de la campagne"""
        for record in self:
            # Supprimer les évaluations existantes
            record.evaluation_ids.unlink()
            
            # Créer les nouvelles évaluations
            evaluation_vals = []
            for criterion in record.campaign_id.criteria_ids:
                score = record._calculate_criterion_score(criterion)
                evaluation_vals.append({
                    'application_id': record.id,
                    'criterion_id': criterion.id,
                    'score': score,
                })
            
            if evaluation_vals:
                self.env['ong.application.evaluation'].create(evaluation_vals)

    def _calculate_criterion_score(self, criterion):
        """Calcul du score pour un critère donné"""
        score = 0.0
        
        try:
            if criterion.code == 'experience':
                score = self._score_experience(criterion.max_score)
            elif criterion.code == 'budget':
                score = self._score_budget(criterion.max_score)
            elif criterion.code == 'staff':
                score = self._score_staff(criterion.max_score)
            elif criterion.code == 'documents':
                score = self._score_documents(criterion.max_score)
            elif criterion.code == 'completeness':
                score = self._score_completeness(criterion.max_score)
            elif criterion.code == 'activity_domains':
                score = self._score_activity_domains(criterion.max_score)
            else:
                # Critère personnalisé ou non reconnu
                score = criterion.max_score * 0.5  # Score par défaut
        
        except Exception as e:
            _logger.warning(f"Erreur lors du calcul du score pour le critère {criterion.code}: {str(e)}")
            score = 0.0
        
        return round(min(score, criterion.max_score), 2)  # S'assurer de ne pas dépasser le max

    def _score_experience(self, max_score):
        """Score basé sur l'expérience"""
        if self.years_experience >= 10:
            return max_score
        elif self.years_experience >= 5:
            return max_score * 0.8
        elif self.years_experience >= 3:
            return max_score * 0.6
        elif self.years_experience >= 1:
            return max_score * 0.4
        else:
            return 0.0

    def _score_budget(self, max_score):
        """Score basé sur le budget"""
        if not self.annual_budget:
            return 0.0
            
        if self.annual_budget >= 1000000:
            return max_score
        elif self.annual_budget >= 500000:
            return max_score * 0.8
        elif self.annual_budget >= 100000:
            return max_score * 0.6
        elif self.annual_budget >= 50000:
            return max_score * 0.4
        elif self.annual_budget >= 10000:
            return max_score * 0.2
        else:
            return 0.0

    def _score_staff(self, max_score):
        """Score basé sur les ressources humaines"""
        total_people = (self.staff_count or 0) + (self.volunteer_count or 0)
        
        if total_people >= 100:
            return max_score
        elif total_people >= 50:
            return max_score * 0.8
        elif total_people >= 20:
            return max_score * 0.6
        elif total_people >= 10:
            return max_score * 0.4
        elif total_people >= 5:
            return max_score * 0.2
        else:
            return 0.0

    def _score_documents(self, max_score):
        """Score basé sur les documents fournis"""
        doc_count = 0
        if self.statute_document:
            doc_count += 1
        if self.certificate_document:
            doc_count += 1
        if self.financial_report:
            doc_count += 1
        
        return (doc_count / 3.0) * max_score

    def _score_completeness(self, max_score):
        """Score basé sur la complétude du profil"""
        fields_to_check = {
            # Champs obligatoires (poids 2)
            'name': 2, 'email': 2, 'registration_number': 2, 'main_activities': 2, 'years_experience': 2,
            # Champs importants (poids 1.5)
            'phone': 1.5, 'city': 1.5, 'funding_sources': 1.5, 'previous_projects': 1.5,
            # Champs optionnels (poids 1)
            'website': 1, 'street': 1, 'references': 1,
        }
        
        total_weight = sum(fields_to_check.values())
        filled_weight = 0
        
        for field, weight in fields_to_check.items():
            value = getattr(self, field)
            if value and (not isinstance(value, str) or value.strip()):
                filled_weight += weight
        
        # Ajouter le poids des champs relationnels
        if self.country_id:
            filled_weight += 1.5
        if self.activity_domains:
            filled_weight += 2
        
        total_weight += 3.5  # Poids des champs relationnels
        
        return (filled_weight / total_weight) * max_score

    def _score_activity_domains(self, max_score):
        """Score basé sur le nombre de domaines d'activité"""
        domain_count = len(self.activity_domains)
        
        if domain_count >= 3:
            return max_score
        elif domain_count == 2:
            return max_score * 0.7
        elif domain_count == 1:
            return max_score * 0.5
        else:
            return 0.0

    def _send_submission_notification(self):
        """Envoyer une notification de soumission"""
        for record in self:
            try:
                # Notification par email (si configuré)
                template = self.env.ref('recrutement_ongs.email_template_application_submitted', raise_if_not_found=False)
                if template:
                    template.send_mail(record.id, force_send=True)
                
                # Message dans le chatter
                record.message_post(
                    body=f"Candidature soumise avec succès le {fields.Datetime.now().strftime('%d/%m/%Y à %H:%M')}",
                    message_type='notification'
                )
            except Exception as e:
                _logger.warning(f"Erreur lors de l'envoi de la notification pour la candidature {record.id}: {str(e)}")

    def action_review(self):
        """Passer la candidature en révision"""
        self.write({'state': 'under_review'})

    def action_select(self):
        """Sélectionner la candidature"""
        self.write({'state': 'selected'})

    def action_reject(self):
        """Rejeter la candidature"""
        self.write({'state': 'rejected'})