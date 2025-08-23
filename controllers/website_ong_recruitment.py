# controllers/website_ong_recruitment.py
# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
from datetime import datetime, date
from odoo.exceptions import ValidationError
from odoo.tools import html_sanitize
import base64
import logging
import re

_logger = logging.getLogger(__name__)

class OngRecruitmentController(http.Controller):

    @http.route(['/ong-recruitment', '/ong-recruitment/campaigns'], type='http', auth="public", website=True)
    def campaign_list(self, **kw):
        """Page de liste des campagnes avec gestion améliorée des descriptions"""
        try:
            # Récupérer les paramètres de filtrage
            search_query = kw.get('search', '')
            state_filter = kw.get('state', '')
            
            # Domaine de base pour les campagnes publiées
            domain = [
                ('website_published', '=', True),
                ('state', 'in', ['open', 'evaluation'])
            ]
            
            # Ajouter les filtres
            if state_filter:
                domain.append(('state', '=', state_filter))
                
            if search_query:
                domain.extend([
                    '|', '|',
                    ('name', 'ilike', search_query),
                    ('description_text', 'ilike', search_query),
                    ('description', 'ilike', search_query)
                ])
            
            # Récupérer les campagnes
            campaigns = request.env['ong.recruitment.campaign'].sudo().search(
                domain, 
                order='state desc, end_date asc'
            )
            
            # Calculer les statistiques pour chaque campagne
            campaign_data = []
            for campaign in campaigns:
                # S'assurer que les champs calculés sont à jour
                campaign._compute_statistics()
                
                # Calculer les jours restants
                days_remaining = None
                if campaign.state == 'open' and campaign.end_date:
                    delta = campaign.end_date - fields.Datetime.now()
                    days_remaining = delta.days
                
                campaign_info = {
                    'campaign': campaign,
                    'days_remaining': days_remaining,
                    'is_urgent': days_remaining is not None and days_remaining <= 7,
                    'description_preview': self._get_description_preview(campaign, 150),
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
            
            # Calculer les statistiques contextuelles
            days_remaining = None
            if campaign.end_date:
                delta = campaign.end_date - fields.Datetime.now()
                days_remaining = delta.days
            
            values = {
                'campaign': campaign,
                'days_remaining': days_remaining,
                'is_urgent': days_remaining is not None and days_remaining <= 7,
                'can_apply': campaign.state == 'open' and (not days_remaining or days_remaining > 0),
                'page_name': 'campaign_detail',
                'page_title': f'Campagne: {campaign.name}',
                'description_safe_html': self._get_safe_html_description(campaign),
                'datetime': datetime,
                'date': date,
            }
            
            return request.render('recrutement_ongs.campaign_detail', values)
            
        except Exception as e:
            _logger.error(f"Erreur lors de l'affichage de la campagne {campaign_id}: {str(e)}")
            return request.render('website.404')

    @http.route(['/ong-recruitment/apply/<int:campaign_id>'], type='http', auth="public", website=True, methods=['GET', 'POST'])
    def apply_campaign(self, campaign_id, **kw):
        """Formulaire de candidature à une campagne avec validation améliorée"""
        try:
            campaign = request.env['ong.recruitment.campaign'].sudo().browse(campaign_id)
            activity_domains = request.env['ong.activity.domain'].sudo().search([('active', '=', True)])
            
            if not campaign.exists() or not campaign.website_published:
                return request.redirect('/ong-recruitment/campaigns')
            
            # Vérifier si la campagne n'est pas expirée
            if campaign.state != 'open' or (campaign.end_date and campaign.end_date < fields.Datetime.now()):
                return request.render('recrutement_ongs.campaign_expired', {'campaign': campaign})
            
            if request.httprequest.method == 'POST':
                # Traiter la soumission du formulaire
                return self._process_application_enhanced(campaign, **kw)
            
            # Récupérer les messages de session
            form_error = request.session.pop('form_error', None)
            form_success = request.session.pop('form_success', None)
            form_data = request.session.pop('form_data', {})
            
            values = {
                'campaign': campaign,
                'activity_domains': activity_domains,
                'countries': request.env['res.country'].sudo().search([]),
                'page_name': 'apply',
                'page_title': f'Candidater: {campaign.name}',
                'criteria': campaign.criteria_ids,
                'form_data': form_data,
                'form_error': form_error,
                'form_success': form_success,
            }
            
            return request.render('recrutement_ongs.application_form', values)
            
        except Exception as e:
            _logger.error(f"Erreur lors de la candidature à la campagne {campaign_id}: {str(e)}")
            return request.render('website.404')

    def _process_application_enhanced(self, campaign, **kw):
        """Traiter une candidature avec validation renforcée"""
        try:
            # Valider les données avec la méthode existante
            self._validate_post_data(kw)
            
            # Vérifier si l'email n'a pas déjà postulé
            existing_application = request.env['ong.application'].sudo().search([
                ('campaign_id', '=', campaign.id),
                ('email', '=', kw.get('email', '').strip().lower())
            ])
            
            if existing_application:
                request.session['form_error'] = "Une candidature avec cet email existe déjà pour cette campagne"
                request.session['form_data'] = kw
                return request.redirect(f'/ong-recruitment/apply/{campaign.id}')
            
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
            
            # Création des évaluations pour les critères si présents
            self._create_criteria_evaluations(application, campaign, kw)
            
            # Soumission de la candidature (déclenche l'évaluation automatique)
            if hasattr(application, 'action_submit'):
                application.action_submit()
            else:
                application.write({'state': 'submitted'})
            
            _logger.info(f"Nouvelle candidature créée: {application.name} (ID: {application.id})")
            
            # Message de succès
            request.session['form_success'] = "Votre candidature a été soumise avec succès !"
            
            return request.redirect(f'/ong-recruitment/application/{application.id}/success')
            
        except ValidationError as e:
            _logger.warning(f"Erreur de validation lors de la soumission: {str(e)}")
            request.session['form_error'] = str(e)
            request.session['form_data'] = kw
            return request.redirect(f'/ong-recruitment/apply/{campaign.id}')
        except ValueError as e:
            _logger.warning(f"Erreur de données lors de la soumission: {str(e)}")
            request.session['form_error'] = f"Erreur dans les données saisies: {str(e)}"
            request.session['form_data'] = kw
            return request.redirect(f'/ong-recruitment/apply/{campaign.id}')
        except Exception as e:
            _logger.error(f"Erreur inattendue lors de la soumission: {str(e)}")
            request.session['form_error'] = "Une erreur inattendue s'est produite. Veuillez réessayer."
            request.session['form_data'] = kw
            return request.redirect(f'/ong-recruitment/apply/{campaign.id}')

    def _create_criteria_evaluations(self, application, campaign, form_data):
        """Créer les évaluations pour les critères de la campagne"""
        try:
            for criterion in campaign.criteria_ids:
                response_key = f'criterion_{criterion.id}'
                if response_key in form_data and form_data[response_key]:
                    score = float(form_data[response_key])
                    request.env['ong.application.evaluation'].sudo().create({
                        'application_id': application.id,
                        'criteria_id': criterion.id,
                        'score': score,
                    })
        except Exception as e:
            _logger.warning(f"Erreur lors de la création des évaluations critères: {e}")

    @http.route(['/ong-recruitment/application/<int:application_id>/success'], type='http', auth="public", website=True)
    def application_success(self, application_id, **kw):
        """Page de confirmation de candidature"""
        try:
            application = request.env['ong.application'].sudo().browse(application_id)
            
            if not application.exists():
                return request.render('website.404')
            
            values = {
                'application': application,
                'campaign': application.campaign_id,
                'page_name': 'success',
                'page_title': 'Candidature Soumise',
            }
            
            return request.render('recrutement_ongs.application_success', values)
            
        except Exception as e:
            _logger.error(f"Erreur lors de l'affichage de la confirmation: {str(e)}")
            return request.render('website.404')

    @http.route(['/ong-recruitment/search'], type='json', auth="public", website=True)
    def search_campaigns(self, term="", **kw):
        """Recherche AJAX de campagnes avec descriptions nettoyées"""
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
                    ('description', 'ilike', term)
                ])
            
            campaigns = request.env['ong.recruitment.campaign'].sudo().search(domain, limit=10)
            
            results = []
            for campaign in campaigns:
                results.append({
                    'id': campaign.id,
                    'name': campaign.name,
                    'description': self._get_description_preview(campaign, 100),
                    'end_date': campaign.end_date.strftime('%d/%m/%Y') if campaign.end_date else '',
                    'max_selections': campaign.max_selections,
                    'state': campaign.state,
                    'url': f'/ong-recruitment/campaign/{campaign.id}'
                })
            
            return {'campaigns': results}
            
        except Exception as e:
            _logger.error(f"Erreur lors de la recherche: {str(e)}")
            return {'error': 'Erreur de recherche'}

    @http.route(['/ong-recruitment/api/campaigns'], type='json', auth='public', website=True)
    def api_campaigns(self, **kwargs):
        """API JSON pour récupérer les campagnes (pour AJAX)"""
        try:
            domain = [('website_published', '=', True)]
            
            # Filtres
            if kwargs.get('state'):
                domain.append(('state', '=', kwargs.get('state')))
            
            if kwargs.get('search'):
                search_term = kwargs.get('search')
                domain.extend([
                    '|', '|', 
                    ('name', 'ilike', search_term),
                    ('description_text', 'ilike', search_term),
                    ('description', 'ilike', search_term)
                ])
            
            campaigns = request.env['ong.recruitment.campaign'].sudo().search(domain)
            
            # Formater les données pour JSON
            campaigns_data = []
            for campaign in campaigns:
                campaigns_data.append({
                    'id': campaign.id,
                    'name': campaign.name,
                    'description_preview': self._get_description_preview(campaign, 150),
                    'state': campaign.state,
                    'start_date': campaign.start_date.isoformat() if campaign.start_date else None,
                    'end_date': campaign.end_date.isoformat() if campaign.end_date else None,
                    'max_selections': campaign.max_selections,
                    'total_applications': campaign.total_applications,
                    'selected_applications': campaign.selected_applications,
                })
            
            return {
                'status': 'success',
                'campaigns': campaigns_data,
                'total': len(campaigns_data)
            }
            
        except Exception as e:
            _logger.error(f"Erreur API campagnes: {e}")
            return {
                'status': 'error',
                'message': 'Erreur lors de la récupération des campagnes'
            }

    @http.route(['/ong-recruitment/application/status/<string:token>'], type='http', auth='public', website=True)
    def application_status_by_token(self, token, **kwargs):
        """Page de suivi du statut d'une candidature via token"""
        try:
            # Rechercher la candidature par token (à implémenter dans le modèle si nécessaire)
            application = request.env['ong.application'].sudo().search([
                ('access_token', '=', token)
            ], limit=1)
            
            if not application:
                return request.render('website.404')
            
            return request.render('recrutement_ongs.application_status', {
                'application': application,
                'campaign': application.campaign_id,
                'page_title': 'Statut de votre candidature',
            })
            
        except Exception as e:
            _logger.error(f"Erreur lors de l'affichage du statut: {e}")
            return request.render('website.404')

    # Méthodes utilitaires pour la gestion des descriptions
    def _get_description_preview(self, campaign, max_length=150):
        """Retourne un aperçu de la description sans HTML"""
        if hasattr(campaign, 'get_description_preview'):
            return campaign.get_description_preview(max_length)
        elif hasattr(campaign, 'description_text') and campaign.description_text:
            text = campaign.description_text
        elif campaign.description:
            # Supprimer les balises HTML manuellement
            text = re.sub('<.*?>', '', campaign.description)
            # Décoder les entités HTML
            import html
            text = html.unescape(text)
            # Nettoyer les espaces multiples
            text = re.sub(r'\s+', ' ', text).strip()
        else:
            return ''
        
        if len(text) <= max_length:
            return text
        
        # Couper au mot le plus proche
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]
        
        return truncated + '...'

    def _get_safe_html_description(self, campaign):
        """Retourne la description HTML sécurisée"""
        if hasattr(campaign, 'get_description_safe_html'):
            return campaign.get_description_safe_html()
        elif campaign.description:
            return html_sanitize(campaign.description)
        else:
            return ''

    # Méthodes existantes conservées
    def _validate_post_data(self, post):
        """Validation des données POST"""
        required_fields = {
            'organization_name': 'Nom de l\'organisation',
            'email': 'Email',
            'registration_number': 'Numéro d\'enregistrement',
            'legal_status': 'Statut légal',
            'main_activities': 'Activités principales',
            'years_experience': 'Années d\'expérience'
        }
        
        errors = []
        for field, label in required_fields.items():
            if not post.get(field) or str(post.get(field)).strip() == '':
                errors.append(f"Le champ '{label}' est obligatoire")
        
        # Validation de l'email
        if post.get('email'):
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, post.get('email')):
                errors.append("L'adresse email n'est pas valide")
        
        # Validation des champs numériques
        numeric_fields = ['annual_budget', 'staff_count', 'volunteer_count', 'years_experience']
        for field in numeric_fields:
            if post.get(field) and post.get(field) != '0':
                try:
                    value = float(post.get(field)) if field == 'annual_budget' else int(post.get(field))
                    if value < 0:
                        errors.append(f"Le champ '{field}' ne peut pas être négatif")
                except (ValueError, TypeError):
                    errors.append(f"Le champ '{field}' doit être un nombre valide")
        
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

        return {
            'campaign_id': campaign_id,
            'name': post.get('organization_name', '').strip(),
            'email': post.get('email', '').strip().lower(),
            'phone': post.get('phone', '').strip(),
            'website': post.get('website', '').strip(),
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
            'state': 'draft',
        }

    def _handle_file_uploads(self, application, post):
        """Gestion de l'upload des fichiers"""
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
                        if file_content:
                            application.write({app_field: base64.b64encode(file_content)})
                    elif isinstance(file_data, bytes):
                        if file_data:
                            application.write({app_field: base64.b64encode(file_data)})
                    elif isinstance(file_data, str) and file_data:
                        try:
                            base64.b64decode(file_data)
                            application.write({app_field: file_data})
                        except Exception:
                            application.write({app_field: base64.b64encode(file_data.encode())})
                except Exception as e:
                    _logger.warning(f"Erreur lors de l'upload du fichier {post_field}: {str(e)}")

    @http.route('/ong-recruitment/application/<int:application_id>', type='http', auth='public', website=True)
    def application_status(self, application_id, **kwargs):
        """Statut d'une candidature"""
        application = request.env['ong.application'].sudo().browse(application_id)
        
        if not application.exists():
            return request.render('website.404')
        
        return request.render('recrutement_ongs.application_status', {
            'application': application,
            'page_title': f'Statut - {application.name}',
        })


# Classe supplémentaire pour compatibilité avec l'ancien code si nécessaire
class WebsiteOngRecruitment(http.Controller):
    """Contrôleur de compatibilité - redirige vers les nouvelles méthodes"""

    @http.route('/ong-recruitment', type='http', auth='public', website=True)
    def recruitment_campaigns(self, **kwargs):
        """Redirection vers la nouvelle méthode"""
        return OngRecruitmentController().campaign_list(**kwargs)

    @http.route('/ong-recruitment/campaign/<int:campaign_id>', type='http', auth='public', website=True)
    def campaign_detail(self, campaign_id, **kwargs):
        """Redirection vers la nouvelle méthode"""
        return OngRecruitmentController().campaign_detail(campaign_id, **kwargs)

    @http.route('/ong-recruitment/apply/<int:campaign_id>', type='http', auth='public', website=True, csrf=True)
    def application_form(self, campaign_id, **kwargs):
        """Redirection vers la nouvelle méthode"""
        return OngRecruitmentController().apply_campaign(campaign_id, **kwargs)

    @http.route('/ong-recruitment/apply/<int:campaign_id>/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def submit_application(self, campaign_id, **post):
        """Redirection vers la nouvelle méthode POST"""
        return OngRecruitmentController().apply_campaign(campaign_id, **post)