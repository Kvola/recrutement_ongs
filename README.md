# README.md
# Module Odoo 17 - Recrutement ONGs

## Vue d'ensemble

Ce module complet permet la gestion transparente du recrutement d'ONGs via Odoo 17, incluant :

- **Candidatures en ligne** via le site web
- **Évaluation automatique** selon critères standards
- **Sélection transparente** des meilleures ONGs
- **Interface administrative** complète

## Données de Démonstration

Le module inclut des données de démonstration réalistes :

### 🏛️ **4 Campagnes Types**
1. **Programme d'Aide Humanitaire 2025** (En cours)
   - 8 positions à pourvoir
   - 4 candidatures soumises avec scores différents
   - Fin dans 30 jours

2. **Initiative Éducation pour Tous** (En cours)
   - 5 positions à pourvoir
   - 2 candidatures de qualité
   - Fin dans 45 jours

3. **Programme Santé Maternelle 2024** (Fermée)
   - 3 ONGs sélectionnées
   - Résultats finalisés
   - Exemple de campagne terminée

4. **Projet Développement Durable 2025** (Brouillon)
   - Campagne en préparation
   - Lancement prévu dans 2 mois

### 🏢 **11 ONGs Diverses**

**ONGs Performantes (Scores 75-90 points):**
- **Action Solidaire Internationale** (CI) - 89.5 pts
  - 12 ans d'expérience, 1.25M€ budget
  - Spécialiste aide humanitaire

- **Santé Pour Tous** (SN) - 79.3 pts
  - 15 ans d'expérience, 2.1M€ budget
  - ONG médicale reconnue

- **Éducation Sans Frontières** (GH) - 76.5 pts
  - 11 ans d'expérience, 1.8M€ budget
  - Spécialiste éducation

**ONGs Moyennes (Scores 50-75 points):**
- **Espoir et Développement** (BF) - 61.8 pts
  - Association locale dynamique
  - 7 ans d'expérience

- **Savoir et Solidarité** (TG) - 61.5 pts
  - Spécialiste alphabétisation
  - Expertise langues locales

**ONGs Débutantes (Scores < 50 points):**
- **Jeunesse et Avenir** (ML) - 49 pts
  - Jeune association (4 ans)
  - Approche innovante

### 📊 **Critères d'Évaluation Standards**

1. **Expérience** (25 points)
   - \>10 ans = 25 pts
   - 5-10 ans = 17.5 pts
   - 2-5 ans = 10 pts

2. **Capacité Financière** (20 points)
   - \>1M€ = 20 pts
   - 500k-1M€ = 16 pts
   - 100-500k€ = 12 pts

3. **Ressources Humaines** (15 points)
   - \>50 personnes = 15 pts
   - 20-50 = 12 pts
   - 10-20 = 9 pts

4. **Documents Légaux** (20 points)
   - 3/3 documents = 20 pts
   - 2/3 documents = 13.3 pts
   - 1/3 documents = 6.7 pts

5. **Complétude Dossier** (20 points)
   - Évaluation qualitative globale

### 🌍 **Couverture Géographique**

ONGs présentes dans 8 pays d'Afrique de l'Ouest :
- Côte d'Ivoire, Burkina Faso, Sénégal, Mali
- Ghana, Togo, Niger, Guinée, Liberia, Sierra Leone

### 🎯 **Domaines d'Activité**

- Aide humanitaire
- Santé
- Éducation
- Développement communautaire
- Droits humains
- Environnement
- Femmes et enfants

## Installation et Test

1. **Installer le module** avec les données de démonstration
2. **Accéder à `/ong-recruitment`** pour voir les campagnes publiques
3. **Tester une candidature** via le formulaire web
4. **Explorer l'interface admin** dans le menu "Recrutement ONGs"

## Scénarios de Test

### Candidature Réussie
- Utiliser la campagne "Programme d'Aide Humanitaire 2025"
- Remplir le formulaire avec données complètes
- Observer le scoring automatique

### Gestion Administrative
- Voir le classement automatique par score
- Tester la sélection automatique
- Consulter les rapports d'évaluation

### Transparence
- Vérifier les critères publiés
- Consulter les scores détaillés
- Suivre l'historique des décisions

Ces données permettent de tester immédiatement toutes les fonctionnalités du module dans un contexte réaliste d'ONGs ouest-africaines.# views/website_templates.xml