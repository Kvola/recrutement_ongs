{
    'name': 'Recrutement ONGs',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Module de recrutement pour ONGs avec candidature en ligne',
    'description': """
Module complet pour le recrutement d'ONGs permettant:
- Création de campagnes de recrutement
- Candidature en ligne via le site web
- Évaluation selon les critères conventionnels des ONGs
- Sélection automatique transparente
    """,
    'author': 'Kavola DIBI',
    'website': 'https://www.iyf.ci',
    'depends': ['base', 'website', 'mail', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/evaluation_criteria_data.xml',
        'views/ong_recruitment_campaign_views.xml',
        'views/ong_application_views.xml',
        'views/ong_evaluation_criteria_views.xml',
        'data/activity_domains_data.xml',
        'data/cron_data.xml',
        'views/website_templates.xml',
        'views/menu_views.xml',
    ],
    'demo': [
        'demo/demo_campaigns.xml',
        'demo/demo_applications.xml',
        'demo/demo_evaluations.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}