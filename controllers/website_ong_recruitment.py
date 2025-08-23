# controllers/website_ong_recruitment.py
# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
from datetime import datetime, date
from odoo.exceptions import ValidationError
from odoo.tools import html_sanitize
from markupsafe import Markup
import base64
import logging
import re

_logger = logging.getLogger(__name__)

class OngRecruitmentController(http.Controller):

    @http.route(['/ong-recruitment', '/ong-recruitment/campaigns'], type='http', auth="public", website=True)
    def campaign_list(self, **kw):
        """Page de liste des campagnes avec descriptions améliorées"""
        try:
            # Récupérer les paramètres de filtrage
            search_query = kw.get('search', '')
            state_filter = kw.get('state', '')
            
            # Domaine de base pour les campagnes publiées
            domain = [('website_published', '=', True)]
            
            # Ajouter les filtres d'état (plus flexible que l'ancienne version)
            if state_filter:
                domain.append(('state', '=', state_filter))
            else:
                # Par défaut, afficher les campagnes ouvertes et en évaluation
                domain.append(('state', 'in', ['open', 'evaluation']))
            
            # Ajouter la recherche textuelle
            if search_query:
                domain.extend([
                    '|', '|',
                    ('name', 'ilike', search_query),
                    ('description_text', 'ilike', search_query),
                    ('organization_name', 'ilike', search_query)
                ])
            
            # Récupérer les campagnes avec tri amélioré
            campaigns = request.env['ong.recruitment.campaign'].sudo().search(
                domain, 
                order='state desc, end_date asc, start_date desc'
            )
            
            # Calculer les statistiques et préparer les données
            campaign_data = []
            for campaign in campaigns:
                # S'assurer que les champs calculés sont à jour
                campaign._compute_statistics()
                
                # Calculer les jours restants
                days_remaining = None
                if campaign.state == 'open' and campaign.end_date:
                    delta = campaign.end_date - fields.Datetime.now()
                    days_remaining = delta.days
                
                # Préparer les données enrichies
                campaign_info = {
                    'campaign': campaign,
                    'days_remaining': days_remaining,
                    'is_urgent': days_remaining is not None and days_remaining <= 7,
                    'description_preview': campaign.get_description_preview(150),
                    'progress_percentage': self._calculate_progress_percentage(campaign),
                }
                campaign_data.append(campaign_info)
            
            values = {
                'campaigns': campaigns,
                'campaign_data': campaign_data,
                'search_query': search_query,
                'state_filter': state_filter,
                'page_name': 'campaigns',
                'page_title': 'Opportunités de Partenariat ONG',
                'datetime': datetime,
                'date': date,
            }
            
            return request.render('recrutement_ongs.campaign_list', values)
            
        except Exception as e:
            _logger.error(f"Erreur lors de l'affichage des campagnes: {str(e)}")
            return request.render('website.404')

    @http.route(['/ong-recruitment/campaign/<int:campaign_id>'], type='http', auth="public", website=True)
    def campaign_detail(self, campaign_id, **kw):
        """Page de détail d'une campagne avec HTML sécurisé"""
        try:
            campaign = request.env['ong.recruitment.campaign'].sudo().browse(campaign_id)
            
            if not campaign.exists() or not campaign.website_published:
                return request.render('website.404')
            
            # Mettre à jour les statistiques
            campaign._compute_statistics()
            
            # Calculer les informations temporelles
            days_remaining = None
            if campaign.end_date:
                delta = campaign.end_date - fields.Datetime.now()
                days_remaining = delta.days
            
            # Préparer les données contextuelles
            values = {
                'campaign': campaign,
                'days_remaining': days_remaining,
                'is_urgent': days_remaining is not None and days_remaining <= 7,
                'can_apply': campaign.state == 'open' and (days_remaining is None or days_remaining > 0),
                'progress_percentage': self._calculate_progress_percentage(campaign),
                'page_name': 'campaign_detail',
                'page_title': f'Campagne: {campaign.name}',
                'datetime': datetime,
                'date': date,
            }
            
            return request.render('recrutement_ongs.campaign_detail', values)
            
        except Exception as e:
            _logger.error(f"Erreur lors de l'affichage de la campagne {campaign_id}: {str(e)}")
            return request.render('website.404')

    @http.route(['/ong-recruitment/apply/<int:campaign_id>'], type='http', auth="public", website=True, methods=['GET', 'POST'])
    def apply_campaign(self, campaign_id, **kw):
        """Formulaire de candidature à une campagne amélioré"""
        try:
            campaign = request.env['ong.recruitment.campaign'].sudo().browse(campaign_id)
            activity_domains = request.env['ong.activity.domain'].sudo().search([('active', '=', True)])
            
            if not campaign.exists() or not campaign.website_published:
                return request.redirect('/ong-recruitment/campaigns')
            
            # Vérifier si la campagne accepte encore les candidatures
            if campaign.state != 'open':
                return self._render_campaign_closed(campaign)
            
            # Vérifier si la campagne n'est pas expirée
            if campaign.end_date and campaign.end_date < fields.Datetime.now():
                return self._render_campaign_expired(campaign)
            
            if request.httprequest.method == 'POST':
                # Traiter la soumission du formulaire avec la nouvelle méthode
                return self._process_application_enhanced(campaign, **kw)
            
            values = {
                'campaign': campaign,
                'activity_domains': activity_domains,
                'countries': request.env['res.country'].sudo().search([]),
                'page_name': 'apply',
                'page_title': f'Candidater: {campaign.name}',
                'form_data': kw,
                'error': request.session.pop('form_error', None),
                'success': request.session.pop('form_success', None),
            }
            
            return request.render('recrutement_ongs.application_form', values)
            
        except Exception as e:
            _logger.error(f"Erreur lors de la candidature à la campagne {campaign_id}: {str(e)}")
            return request.render('website.404')

    def _process_application_enhanced(self, campaign, **kw):
        """Traiter une candidature avec validation améliorée"""
        try:
            # Validation complète des données
            self._validate_post_data(kw)
            
            # Vérifier les doublons d'email pour cette campagne
            existing_application = request.env['ong.application'].sudo().search([
                ('campaign_id', '=', campaign.id),
                ('email', '=', kw.get('email', '').strip().lower())
            ])
            
            if existing_application:
                raise ValidationError("Une candidature avec cet email existe déjà pour cette campagne")
            
            # Traitement des domaines d'activité
            activity_domains = self._process_activity_domains(kw.get('activity_domains'))
            
            # Préparation des valeurs pour la création
            application_vals = self._prepare_application_values(campaign.id, kw)
            
            # Création de la candidature
            application = request.env['ong.application'].sudo().create(application_vals)
            
            # Gestion des domaines d'activité
            if activity_domains:
                application.write({'activity_domains': [(6, 0, activity_domains)]})
            
            # Gestion des fichiers uploadés
            self._handle_file_uploads(application, kw)
            
            # Créer les évaluations pour chaque critère si ils existent
            if campaign.criteria_ids:
                self._create_criteria_evaluations(application, campaign, kw)
            
            # Soumission de la candidature (déclenche l'évaluation automatique)
            application.action_submit()
            
            _logger.info(f"Nouvelle candidature créée: {application.name} (ID: {application.id})")
            
            # Message de succès
            request.session['form_success'] = "Votre candidature a été soumise avec succès !"
            
            return request.redirect(f'/ong-recruitment/application/{application.id}/success')
            
        except ValidationError as e:
            _logger.warning(f"Erreur de validation lors de la soumission: {str(e)}")
            request.session['form_error'] = str(e)
            return request.redirect(f'/ong-recruitment/apply/{campaign.id}')
        except Exception as e:
            _logger.error(f"Erreur lors du traitement de la candidature: {str(e)}")
            request.session['form_error'] = "Une erreur s'est produite. Veuillez réessayer."
            return request.redirect(f'/ong-recruitment/apply/{campaign.id}')

    def _validate_post_data(self, post):
        """Validation complète des données POST"""
        required_fields = {
            'name': 'Nom du contact',
            'email': 'Email',
            'organization_name': 'Nom de l\'organisation',
            'registration_number': 'Numéro d\'enregistrement',
            'legal_status': 'Statut légal',
            'main_activities': 'Activités principales',
            'years_experience': 'Années d\'expérience'
        }
        
        errors = []
        
        # Validation des champs obligatoires
        for field, label in required_fields.items():
            if not post.get(field) or str(post.get(field)).strip() == '':
                errors.append(f"Le champ '{label}' est obligatoire")
        
        # Validation de l'email
        if post.get('email'):
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, post.get('email')):
                errors.append("L'adresse email n'est pas valide")
        
        # Validation des champs numériques
        numeric_fields = {
            'annual_budget': 'Budget annuel',
            'staff_count': 'Nombre d\'employés',
            'volunteer_count': 'Nombre de bénévoles',
            'years_experience': 'Années d\'expérience'
        }
        
        for field, label in numeric_fields.items():
            if post.get(field) and str(post.get(field)).strip():
                try:
                    value = float(post.get(field)) if field == 'annual_budget' else int(post.get(field))
                    if value < 0:
                        errors.append(f"Le champ '{label}' ne peut pas être négatif")
                except (ValueError, TypeError):
                    errors.append(f"Le champ '{label}' doit être un nombre valide")
        
        # Validation de l'URL du site web
        if post.get('website') and post.get('website').strip():
            website = post.get('website').strip()
            if not website.startswith(('http://', 'https://')):
                website = 'https://' + website
            # Validation basique de l'URL
            url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}.*$'
            if not re.match(url_pattern, website):
                errors.append("L'URL du site web n'est pas valide")
        
        if errors:
            raise ValidationError('\n'.join(errors))

    def _process_activity_domains(self, activity_domains_data):
        """Traitement des domaines d'activité"""
        if not activity_domains_data:
            return []
        
        try:
            if isinstance(activity_domains_data, list):
                return [int(d) for d in activity_domains_data if str(d).isdigit()]
            elif isinstance(activity_domains_data, str):
                if activity_domains_data.isdigit():
                    return [int(activity_domains_data)]
                else:
                    return [int(d.strip()) for d in activity_domains_data.split(',') if d.strip().isdigit()]
            else:
                return [int(activity_domains_data)]
        except (ValueError, TypeError):
            _logger.warning(f"Erreur lors du traitement des domaines d'activité: {activity_domains_data}")
            return []

    def _prepare_application_values(self, campaign_id, post):
        """Préparation des valeurs pour la création de la candidature"""
        def safe_float(value, default=0.0):
            try:
                return float(value) if value and str(value).strip() != '' else default
            except (ValueError, TypeError):
                return default

        def safe_int(value, default=0):
            try:
                return int(value) if value and str(value).strip() != '' else default
            except (ValueError, TypeError):
                return default

        # Validation et conversion du country_id
        country_id = False
        if post.get('country_id'):
            try:
                country_id = int(post.get('country_id'))
                country = request.env['res.country'].sudo().browse(country_id)
                if not country.exists():
                    country_id = False
            except (ValueError, TypeError):
                country_id = False

        # Traitement de l'URL du site web
        website = post.get('website', '').strip()
        if website and not website.startswith(('http://', 'https://')):
            website = 'https://' + website

        return {
            'campaign_id': campaign_id,
            'name': post.get('name', '').strip(),
            'email': post.get('email', '').strip().lower(),
            'phone': post.get('phone', '').strip(),
            'website': website,
            'organization_name': post.get('organization_name', '').strip(),
            'organization_type': post.get('organization_type'),
            'street': post.get('street', '').strip(),
            'city': post.get('city', '').strip(),
            'country_id': country_id,
            'registration_number': post.get('registration_number', '').strip(),
            'legal_status': post.get('legal_status'),
            'main_activities': post.get('main_activities', '').strip(),
            'annual_budget': safe_float(post.get('annual_budget')),
            'funding_sources': post.get('funding_sources', '').strip(),
            'staff_count': safe_int(post.get('staff_count')),
            'volunteer_count': safe_int(post.get('volunteer_count')),
            'years_experience': safe_int(post.get('years_experience')),
            'previous_projects': post.get('previous_projects', '').strip(),
            'references': post.get('references', '').strip(),
            'description': post.get('description', '').strip(),
            'state': 'draft',
        }

    def _handle_file_uploads(self, application, post):
        """Gestion améliorée de l'upload des fichiers"""
        file_fields = [
            ('statute_document', 'statute_document'),
            ('certificate_document', 'certificate_document'),
            ('financial_report', 'financial_report')
        ]
        
        for post_field, app_field in file_fields:
            if post_field in post and post[post_field]:
                try:
                    file_data = post[post_field]
                    if hasattr(file_data, 'read'):
                        file_content = file_data.read()
                        if file_content and len(file_content) > 0:
                            application.write({app_field: base64.b64encode(file_content)})
                    elif isinstance(file_data, bytes) and len(file_data) > 0:
                        application.write({app_field: base64.b64encode(file_data)})
                    elif isinstance(file_data, str) and file_data:
                        try:
                            base64.b64decode(file_data)
                            application.write({app_field: file_data})
                        except Exception:
                            application.write({app_field: base64.b64encode(file_data.encode())})
                except Exception as e:
                    _logger.warning(f"Erreur lors de l'upload du fichier {post_field}: {str(e)}")

    def _create_criteria_evaluations(self, application, campaign, post):
        """Créer les évaluations pour chaque critère"""
        for criterion in campaign.criteria_ids:
            response_key = f'criterion_{criterion.id}'
            if response_key in post:
                try:
                    score = float(post[response_key])
                    if 0 <= score <= 100:  # Validation du score
                        request.env['ong.application.evaluation'].sudo().create({
                            'application_id': application.id,
                            'criteria_id': criterion.id,
                            'score': score,
                        })
                except (ValueError, TypeError):
                    _logger.warning(f"Score invalide pour le critère {criterion.id}: {post[response_key]}")

    def _calculate_progress_percentage(self, campaign):
        """Calculer le pourcentage de progression des candidatures"""
        if campaign.max_selections <= 0:
            return 0
        max_applications = campaign.max_selections * 3  # Limite à 3 fois le nombre de sélections
        return min(100, (campaign.total_applications / max_applications) * 100)

    def _render_campaign_closed(self, campaign):
        """Rendu pour campagne fermée"""
        return request.render('recrutement_ongs.campaign_closed', {
            'campaign': campaign,
            'page_title': f'Campagne fermée: {campaign.name}',
        })

    def _render_campaign_expired(self, campaign):
        """Rendu pour campagne expirée"""
        return request.render('recrutement_ongs.campaign_expired', {
            'campaign': campaign,
            'page_title': f'Campagne expirée: {campaign.name}',
        })

    @http.route(['/ong-recruitment/application/<int:application_id>/success'], type='http', auth="public", website=True)
    def application_success(self, application_id, **kw):
        """Page de confirmation de candidature améliorée"""
        try:
            application = request.env['ong.application'].sudo().browse(application_id)
            
            if not application.exists():
                return request.render('website.404')
            
            # Générer un token d'accès si il n'existe pas
            if not hasattr(application, 'access_token') or not application.access_token:
                import secrets
                application.sudo().write({'access_token': secrets.token_urlsafe(32)})
            
            values = {
                'application': application,
                'campaign': application.campaign_id,
                'page_name': 'success',
                'page_title': 'Candidature Soumise avec Succès',
            }
            
            return request.render('recrutement_ongs.application_success', values)
            
        except Exception as e:
            _logger.error(f"Erreur lors de l'affichage de la confirmation: {str(e)}")
            return request.render('website.404')

    @http.route(['/ong-recruitment/application/<int:application_id>/status'], type='http', auth="public", website=True)
    def application_status(self, application_id, token=None, **kwargs):
        """Page de suivi du statut d'une candidature"""
        try:
            application = request.env['ong.application'].sudo().browse(application_id)
            
            if not application.exists():
                return request.render('website.404')
            
            # Vérifier le token si fourni
            if token and hasattr(application, 'access_token'):
                if application.access_token != token:
                    return request.render('website.403')
            
            values = {
                'application': application,
                'campaign': application.campaign_id,
                'page_name': 'status',
                'page_title': f'Statut de votre candidature',
            }
            
            return request.render('recrutement_ongs.application_status', values)
            
        except Exception as e:
            _logger.error(f"Erreur lors de l'affichage du statut: {str(e)}")
            return request.render('website.404')

    @http.route(['/ong-recruitment/search'], type='json', auth="public", website=True)
    def search_campaigns(self, term="", **kw):
        """Recherche AJAX de campagnes améliorée"""
        try:
            domain = [
                ('website_published', '=', True),
                ('state', 'in', ['open', 'evaluation'])
            ]
            
            if term:
                domain.extend([
                    '|', '|',
                    ('name', 'ilike', term),
                    ('description_text', 'ilike', term),
                    ('organization_name', 'ilike', term)
                ])
            
            campaigns = request.env['ong.recruitment.campaign'].sudo().search(domain, limit=10)
            
            results = []
            for campaign in campaigns:
                # Utiliser la nouvelle méthode de prévisualisation
                description_preview = campaign.get_description_preview(100) if hasattr(campaign, 'get_description_preview') else (
                    campaign.description_text[:100] + '...' if campaign.description_text else 
                    (campaign.description[:100] + '...' if campaign.description else '')
                )
                
                results.append({
                    'id': campaign.id,
                    'name': campaign.name,
                    'description': description_preview,
                    'end_date': campaign.end_date.strftime('%d/%m/%Y') if campaign.end_date else '',
                    'max_selections': campaign.max_selections,
                    'total_applications': campaign.total_applications,
                    'state': campaign.state,
                    'state_label': dict(campaign._fields['state'].selection)[campaign.state],
                    'url': f'/ong-recruitment/campaign/{campaign.id}',
                    'can_apply': campaign.state == 'open'
                })
            
            return {
                'status': 'success',
                'campaigns': results,
                'total': len(results)
            }
            
        except Exception as e:
            _logger.error(f"Erreur lors de la recherche: {str(e)}")
            return {
                'status': 'error',
                'message': 'Erreur de recherche',
                'campaigns': []
            }

    @http.route(['/ong-recruitment/api/campaigns'], type='json', auth='public', website=True)
    def api_campaigns(self, **kwargs):
        """API JSON complète pour récupérer les campagnes"""
        try:
            domain = [('website_published', '=', True)]
            
            # Filtres
            if kwargs.get('state'):
                domain.append(('state', '=', kwargs.get('state')))
            else:
                domain.append(('state', 'in', ['open', 'evaluation']))
            
            if kwargs.get('search'):
                search_term = kwargs.get('search')
                domain.extend([
                    '|', '|',
                    ('name', 'ilike', search_term),
                    ('description_text', 'ilike', search_term),
                    ('organization_name', 'ilike', search_term)
                ])
            
            # Pagination
            limit = min(int(kwargs.get('limit', 20)), 100)  # Max 100 résultats
            offset = int(kwargs.get('offset', 0))
            
            campaigns = request.env['ong.recruitment.campaign'].sudo().search(
                domain, 
                limit=limit, 
                offset=offset,
                order='state desc, end_date asc'
            )
            
            # Formater les données pour JSON
            campaigns_data = []
            for campaign in campaigns:
                days_remaining = None
                if campaign.end_date:
                    delta = campaign.end_date - fields.Datetime.now()
                    days_remaining = delta.days
                
                campaigns_data.append({
                    'id': campaign.id,
                    'name': campaign.name,
                    'description_preview': campaign.get_description_preview(150) if hasattr(campaign, 'get_description_preview') else '',
                    'state': campaign.state,
                    'state_label': dict(campaign._fields['state'].selection)[campaign.state],
                    'start_date': campaign.start_date.isoformat() if campaign.start_date else None,
                    'end_date': campaign.end_date.isoformat() if campaign.end_date else None,
                    'days_remaining': days_remaining,
                    'is_urgent': days_remaining is not None and days_remaining <= 7,
                    'max_selections': campaign.max_selections,
                    'total_applications': campaign.total_applications,
                    'selected_applications': campaign.selected_applications,
                    'progress_percentage': self._calculate_progress_percentage(campaign),
                    'can_apply': campaign.state == 'open' and (days_remaining is None or days_remaining > 0),
                    'url': f'/ong-recruitment/campaign/{campaign.id}',
                    'apply_url': f'/ong-recruitment/apply/{campaign.id}' if campaign.state == 'open' else None,
                })
            
            return {
                'status': 'success',
                'campaigns': campaigns_data,
                'total': len(campaigns_data),
                'has_more': len(campaigns_data) == limit
            }
            
        except Exception as e:
            _logger.error(f"Erreur API campagnes: {e}")
            return {
                'status': 'error',
                'message': 'Erreur lors de la récupération des campagnes',
                'campaigns': [],
                'total': 0
            }