# models/ong_evaluation_criteria.py
# -*- coding: utf-8 -*-
from odoo import models, fields

class OngEvaluationCriteria(models.Model):
    _name = 'ong.evaluation.criteria'
    _description = 'Critères d\'Évaluation ONG'
    _order = 'sequence, name'

    name = fields.Char('Nom du Critère', required=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description')
    max_score = fields.Float('Score Maximum', required=True, default=20.0)
    weight = fields.Float('Poids (%)', default=100.0)
    sequence = fields.Integer('Séquence', default=10)
    active = fields.Boolean('Actif', default=True)


class OngApplicationEvaluation(models.Model):
    _name = 'ong.application.evaluation'
    _description = 'Évaluation de Candidature ONG'

    application_id = fields.Many2one('ong.application', string='Candidature', required=True)
    criterion_id = fields.Many2one('ong.evaluation.criteria', string='Critère', required=True)
    score = fields.Float('Score', required=True)
    notes = fields.Text('Notes')


class OngActivityDomain(models.Model):
    _name = 'ong.activity.domain'
    _description = 'Domaine d\'Activité ONG'

    name = fields.Char('Nom', required=True)
    description = fields.Text('Description')
    active = fields.Boolean('Actif', default=True)