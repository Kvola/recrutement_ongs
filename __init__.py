# __init__.py
# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import wizards

def post_init_hook(cr, registry):
    """Hook exécuté après l'installation du module"""
    from odoo import api, SUPERUSER_ID
    import logging
    
    _logger = logging.getLogger(__name__)
    _logger.info("Initialisation du module Recrutement ONGs...")
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    try:
        # Créer les critères d'évaluation par défaut s'ils n'existent pas
        criteria_data = [
            {
                'name': 'Expérience',
                'code': 'experience',
                'description': 'Années d\'expérience de l\'organisation',
                'max_score': 20.0,
                'weight': 100.0,
                'sequence': 10,
            },
            {
                'name': 'Capacité Financière',
                'code': 'budget',
                'description': 'Budget annuel et sources de financement',
                'max_score': 20.0,
                'weight': 100.0,
                'sequence': 20,
            },
            {
                'name': 'Ressources Humaines',
                'code': 'staff',
                'description': 'Nombre d\'employés et de bénévoles',
                'max_score': 15.0,
                'weight': 100.0,
                'sequence': 30,
            },
            {
                'name': 'Documents Fournis',
                'code': 'documents',
                'description': 'Complétude des documents requis',
                'max_score': 15.0,
                'weight': 100.0,
                'sequence': 40,
            },
            {
                'name': 'Complétude du Profil',
                'code': 'completeness',
                'description': 'Complétude des informations fournies',
                'max_score': 20.0,
                'weight': 100.0,
                'sequence': 50,
            },
            {
                'name': 'Domaines d\'Activité',
                'code': 'activity_domains',
                'description': 'Pertinence et nombre de domaines d\'activité',
                'max_score': 10.0,
                'weight': 100.0,
                'sequence': 60,
            }
        ]
        
        criteria_model = env['ong.evaluation.criteria']
        for criteria in criteria_data:
            existing = criteria_model.search([('code', '=', criteria['code'])], limit=1)
            if not existing:
                criteria_model.create(criteria)
                _logger.info(f"Critère d'évaluation créé: {criteria['name']}")
        
        # Créer les domaines d'activité par défaut
        domains_data = [
            {'name': 'Santé', 'description': 'Services de santé et soins médicaux'},
            {'name': 'Éducation', 'description': 'Programmes éducatifs et formation'},
            {'name': 'Développement Rural', 'description': 'Agriculture et développement des zones rurales'},
            {'name': 'Environnement', 'description': 'Protection de l\'environnement et développement durable'},
            {'name': 'Droits Humains', 'description': 'Défense des droits de l\'homme et justice sociale'},
            {'name': 'Aide Humanitaire', 'description': 'Secours d\'urgence et aide humanitaire'},
            {'name': 'Développement Économique', 'description': 'Microfinance et développement économique'},
            {'name': 'Genre et Égalité', 'description': 'Promotion de l\'égalité des genres'},
            {'name': 'Enfance et Jeunesse', 'description': 'Protection et développement de l\'enfance'},
            {'name': 'Eau et Assainissement', 'description': 'Accès à l\'eau potable et assainissement'},
        ]
        
        domains_model = env['ong.activity.domain']
        for domain in domains_data:
            existing = domains_model.search([('name', '=', domain['name'])], limit=1)
            if not existing:
                domains_model.create(domain)
                _logger.info(f"Domaine d'activité créé: {domain['name']}")
        
        # Configurer les paramètres système
        config_params = [
            ('ong.auto_evaluation', 'True'),
            ('ong.email_notifications', 'True'),
            ('ong.max_file_size', '5'),  # MB
            ('ong.dashboard_refresh_interval', '300'),  # secondes
        ]
        
        for key, value in config_params:
            env['ir.config_parameter'].sudo().set_param(key, value)
            _logger.info(f"Paramètre configuré: {key} = {value}")
        
        _logger.info("Module Recrutement ONGs initialisé avec succès!")
        
    except Exception as e:
        _logger.error(f"Erreur lors de l'initialisation du module: {str(e)}")
        raise

def uninstall_hook(cr, registry):
    """Hook exécuté lors de la désinstallation du module"""
    from odoo import api, SUPERUSER_ID
    import logging
    
    _logger = logging.getLogger(__name__)
    _logger.info("Désinstallation du module Recrutement ONGs...")
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    try:
        # Supprimer les paramètres système
        config_keys = [
            'ong.auto_evaluation',
            'ong.email_notifications', 
            'ong.max_file_size',
            'ong.dashboard_refresh_interval',
        ]
        
        for key in config_keys:
            env['ir.config_parameter'].sudo().search([('key', '=', key)]).unlink()
            _logger.info(f"Paramètre supprimé: {key}")
        
        # Nettoyer les tâches cron créées par le module
        cron_jobs = env['ir.cron'].search([
            ('cron_name', 'ilike', 'ong%'),
            ('model_id.model', 'in', [
                'ong.recruitment.campaign',
                'ong.application',
                'ong.dashboard.report'
            ])
        ])
        
        if cron_jobs:
            cron_jobs.write({'active': False})
            _logger.info(f"{len(cron_jobs)} tâches cron désactivées")
        
        # Nettoyer les attachments orphelins
        orphan_attachments = env['ir.attachment'].search([
            ('res_model', 'in', [
                'ong.application',
                'ong.recruitment.campaign',
                'ong.dashboard.report'
            ]),
            ('res_id', '=', 0)
        ])
        
        if orphan_attachments:
            orphan_attachments.unlink()
            _logger.info(f"{len(orphan_attachments)} attachments orphelins supprimés")
        
        _logger.info("Module Recrutement ONGs désinstallé avec succès!")
        
    except Exception as e:
        _logger.error(f"Erreur lors de la désinstallation du module: {str(e)}")
        # Ne pas lever l'exception pour ne pas bloquer la désinstallation