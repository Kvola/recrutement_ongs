/** @odoo-module **/

import { Component, onWillStart, useState, onMounted } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { loadJS, loadCSS } from '@web/core/assets';

export class OngDashboardWidget extends Component {
    static template = 'recrutement_ongs.DashboardWidget';
    
    setup() {
        this.rpc = useService('rpc');
        this.notification = useService('notification');
        this.actionService = useService('action');
        
        this.state = useState({
            data: {},
            loading: true,
            error: null,
            analytics: {
                trends: {},
                insights: [],
                recommendations: []
            }
        });
        
        onWillStart(async () => {
            await this.loadChartLibrary();
        });
        
        onMounted(() => {
            this.loadDashboardData();
        });
    }
    
    async loadChartLibrary() {
        try {
            await this.loadChartJSWithFallback();
            await loadCSS('/recrutement_ongs/static/src/css/dashboard.css');
        } catch (error) {
            console.error('Failed to load Chart.js:', error);
            this.notification.add('Impossible de charger la bibliothèque de graphiques', { type: 'warning' });
        }
    }
    
    async loadChartJSWithFallback() {
        const cdnUrls = [
            '/recrutement_ongs/static/lib/chart.js/chart.umd.js',
            'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.js',
            'https://unpkg.com/chart.js@4.4.0/dist/chart.umd.js',
            'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js'
        ];
        
        for (const url of cdnUrls) {
            try {
                await loadJS(url);
                console.log(`Chart.js loaded successfully from: ${url}`);
                return;
            } catch (error) {
                console.warn(`Failed to load Chart.js from ${url}:`, error);
                continue;
            }
        }
        
        throw new Error('Could not load Chart.js from any source');
    }
    
    async loadDashboardData() {
        try {
            this.state.loading = true;
            this.state.error = null;
            
            const result = await this.rpc('/ong/dashboard/data', {});
            
            if (result && result.error) {
                this.state.error = result.error;
                this.notification.add('Erreur lors du chargement des données', { type: 'danger' });
            } else if (result) {
                this.state.data = result;
                this.generateAnalytics();
                if (typeof Chart !== 'undefined') {
                    this.renderCharts();
                } else {
                    this.notification.add('Les graphiques ne peuvent pas être affichés', { type: 'info' });
                }
            } else {
                this.state.error = "Aucune donnée reçue";
                this.notification.add('Aucune donnée disponible', { type: 'warning' });
            }
        } catch (error) {
            console.error('Dashboard data loading error:', error);
            this.state.error = error.message || 'Erreur inconnue';
            this.notification.add('Erreur de connexion au serveur', { type: 'danger' });
        } finally {
            this.state.loading = false;
        }
    }
    
    generateAnalytics() {
        const data = this.state.data;
        if (!data || !data.stats) return;
        
        // Calculate trends and insights
        const insights = [];
        const recommendations = [];
        
        // Success rate analysis
        const successRate = data.stats.total_applications > 0 
            ? (data.stats.selected_ongs / data.stats.total_applications) * 100 
            : 0;
        
        if (successRate > 80) {
            insights.push({
                type: 'success',
                icon: 'fa-arrow-up',
                title: 'Taux de sélection excellent',
                description: `${successRate.toFixed(1)}% des candidatures sont acceptées`,
                trend: 'positive'
            });
        } else if (successRate < 20) {
            insights.push({
                type: 'warning',
                icon: 'fa-arrow-down',
                title: 'Taux de sélection faible',
                description: `Seulement ${successRate.toFixed(1)}% des candidatures sont acceptées`,
                trend: 'negative'
            });
            recommendations.push({
                priority: 'high',
                title: 'Améliorer les critères de sélection',
                description: 'Revoir les critères d\'éligibilité pour optimiser le taux de sélection',
                action: 'review_criteria'
            });
        }
        
        // Application volume analysis
        const avgApplicationsPerCampaign = data.stats.total_campaigns > 0 
            ? data.stats.total_applications / data.stats.total_campaigns 
            : 0;
        
        if (avgApplicationsPerCampaign < 5) {
            insights.push({
                type: 'info',
                icon: 'fa-users',
                title: 'Participation limitée',
                description: `Moyenne de ${avgApplicationsPerCampaign.toFixed(1)} candidatures par campagne`,
                trend: 'neutral'
            });
            recommendations.push({
                priority: 'medium',
                title: 'Augmenter la visibilité',
                description: 'Améliorer la communication pour attirer plus de candidatures',
                action: 'improve_visibility'
            });
        }
        
        // Active campaigns analysis
        const activeCampaignRatio = data.stats.total_campaigns > 0 
            ? (data.stats.active_campaigns / data.stats.total_campaigns) * 100 
            : 0;
        
        if (activeCampaignRatio > 50) {
            insights.push({
                type: 'info',
                icon: 'fa-calendar-check',
                title: 'Forte activité',
                description: `${activeCampaignRatio.toFixed(0)}% des campagnes sont actives`,
                trend: 'positive'
            });
        }
        
        // Seasonal trends (mock data for demonstration)
        const currentMonth = new Date().getMonth();
        if (currentMonth >= 8 && currentMonth <= 11) { // Sept-Dec
            recommendations.push({
                priority: 'medium',
                title: 'Période de forte demande',
                description: 'Préparer les ressources pour la saison de recrutement',
                action: 'prepare_resources'
            });
        }
        
        this.state.analytics = {
            trends: {
                successRate: successRate,
                avgApplications: avgApplicationsPerCampaign,
                activeCampaignRatio: activeCampaignRatio
            },
            insights: insights,
            recommendations: recommendations
        };
    }
    
    renderCharts() {
        setTimeout(() => {
            try {
                this.renderStatesChart();
                this.renderCountriesChart();
                this.renderMonthlyChart();
                this.renderScoreChart();
                this.renderDomainsChart();
                this.renderTrendsChart();
                this.renderPerformanceChart();
            } catch (error) {
                console.error('Error rendering charts:', error);
                this.notification.add('Erreur lors de l\'affichage des graphiques', { type: 'warning' });
            }
        }, 100);
    }
    
    renderStatesChart() {
        const ctx = document.getElementById('statesChart');
        if (!ctx || !this.state.data.charts || typeof Chart === 'undefined') return;
        
        if (this.statesChartInstance) {
            this.statesChartInstance.destroy();
        }
        
        const chartData = this.state.data.charts.applications_by_state || { labels: [], data: [] };
        
        this.statesChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: chartData.labels,
                datasets: [{
                    data: chartData.data,
                    backgroundColor: [
                        'rgba(99, 102, 241, 0.8)',
                        'rgba(59, 130, 246, 0.8)', 
                        'rgba(16, 185, 129, 0.8)',
                        'rgba(245, 158, 11, 0.8)',
                        'rgba(239, 68, 68, 0.8)',
                        'rgba(156, 163, 175, 0.8)'
                    ],
                    borderWidth: 0,
                    hoverBorderWidth: 3,
                    hoverBorderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            font: { size: 12 },
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        cornerRadius: 8
                    }
                }
            }
        });
    }
    
    renderCountriesChart() {
        const ctx = document.getElementById('countriesChart');
        if (!ctx || !this.state.data.charts || typeof Chart === 'undefined') return;
        
        if (this.countriesChartInstance) {
            this.countriesChartInstance.destroy();
        }
        
        const chartData = this.state.data.charts.applications_by_country || { labels: [], data: [] };
        
        this.countriesChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Candidatures',
                    data: chartData.data,
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 0,
                    borderRadius: 6,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        cornerRadius: 8
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)',
                            drawBorder: false
                        },
                        ticks: {
                            stepSize: 1,
                            font: { size: 11 },
                            color: '#6b7280'
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: {
                            font: { size: 11 },
                            color: '#6b7280'
                        }
                    }
                }
            }
        });
    }
    
    renderMonthlyChart() {
        const ctx = document.getElementById('monthlyChart');
        if (!ctx || !this.state.data.charts || typeof Chart === 'undefined') return;
        
        if (this.monthlyChartInstance) {
            this.monthlyChartInstance.destroy();
        }
        
        const chartData = this.state.data.charts.monthly_applications || { labels: [], data: [] };
        
        this.monthlyChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Candidatures',
                    data: chartData.data,
                    borderColor: 'rgba(16, 185, 129, 1)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: 'rgba(16, 185, 129, 1)',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        cornerRadius: 8
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)',
                            drawBorder: false
                        },
                        ticks: {
                            stepSize: 1,
                            font: { size: 11 },
                            color: '#6b7280'
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: {
                            font: { size: 11 },
                            color: '#6b7280'
                        }
                    }
                }
            }
        });
    }
    
    renderScoreChart() {
        const ctx = document.getElementById('scoreChart');
        if (!ctx || !this.state.data.charts || typeof Chart === 'undefined') return;
        
        if (this.scoreChartInstance) {
            this.scoreChartInstance.destroy();
        }
        
        const chartData = this.state.data.charts.score_distribution || { labels: [], data: [] };
        
        this.scoreChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Nombre d\'ONGs',
                    data: chartData.data,
                    backgroundColor: [
                        'rgba(239, 68, 68, 0.8)',   // Rouge
                        'rgba(245, 158, 11, 0.8)',  // Orange
                        'rgba(251, 191, 36, 0.8)',  // Jaune
                        'rgba(16, 185, 129, 0.8)',  // Vert
                        'rgba(6, 182, 212, 0.8)',   // Cyan
                        'rgba(99, 102, 241, 0.8)'   // Indigo
                    ],
                    borderWidth: 0,
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        cornerRadius: 8
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)',
                            drawBorder: false
                        },
                        ticks: {
                            stepSize: 1,
                            font: { size: 11 },
                            color: '#6b7280'
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: {
                            font: { size: 11 },
                            color: '#6b7280'
                        }
                    }
                }
            }
        });
    }
    
    renderDomainsChart() {
        const ctx = document.getElementById('domainsChart');
        if (!ctx || !this.state.data.charts || typeof Chart === 'undefined') return;
        
        if (this.domainsChartInstance) {
            this.domainsChartInstance.destroy();
        }
        
        const chartData = this.state.data.charts.top_activity_domains || { labels: [], data: [] };
        
        this.domainsChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Candidatures',
                    data: chartData.data,
                    backgroundColor: 'rgba(147, 51, 234, 0.8)',
                    borderColor: 'rgba(147, 51, 234, 1)',
                    borderWidth: 0,
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        cornerRadius: 8
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)',
                            drawBorder: false
                        },
                        ticks: {
                            stepSize: 1,
                            font: { size: 11 },
                            color: '#6b7280'
                        }
                    },
                    y: {
                        grid: { display: false },
                        ticks: {
                            font: { size: 11 },
                            color: '#6b7280'
                        }
                    }
                }
            }
        });
    }
    
    renderTrendsChart() {
        const ctx = document.getElementById('trendsChart');
        if (!ctx || typeof Chart === 'undefined') return;
        
        if (this.trendsChartInstance) {
            this.trendsChartInstance.destroy();
        }
        
        // Mock trend data
        const trendData = {
            labels: ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun'],
            applications: [45, 62, 38, 71, 56, 89],
            selections: [12, 18, 8, 22, 16, 28]
        };
        
        this.trendsChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: trendData.labels,
                datasets: [{
                    label: 'Candidatures',
                    data: trendData.applications,
                    borderColor: 'rgba(59, 130, 246, 1)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: false,
                    pointRadius: 4
                }, {
                    label: 'Sélections',
                    data: trendData.selections,
                    borderColor: 'rgba(16, 185, 129, 1)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: false,
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            font: { size: 12 },
                            usePointStyle: true
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)',
                            drawBorder: false
                        },
                        ticks: {
                            font: { size: 11 },
                            color: '#6b7280'
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: {
                            font: { size: 11 },
                            color: '#6b7280'
                        }
                    }
                }
            }
        });
    }
    
    renderPerformanceChart() {
        const ctx = document.getElementById('performanceChart');
        if (!ctx || typeof Chart === 'undefined') return;
        
        if (this.performanceChartInstance) {
            this.performanceChartInstance.destroy();
        }
        
        const performanceData = {
            labels: ['Qualité', 'Délai', 'Budget', 'Innovation', 'Impact'],
            data: [85, 72, 68, 91, 79]
        };
        
        this.performanceChartInstance = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: performanceData.labels,
                datasets: [{
                    label: 'Performance',
                    data: performanceData.data,
                    borderColor: 'rgba(99, 102, 241, 1)',
                    backgroundColor: 'rgba(99, 102, 241, 0.2)',
                    pointBackgroundColor: 'rgba(99, 102, 241, 1)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        pointLabels: {
                            font: { size: 11 },
                            color: '#6b7280'
                        }
                    }
                }
            }
        });
    }
    
    async refreshData() {
        await this.loadDashboardData();
    }
    
    exportDashboard(format) {
        try {
            window.open(`/ong/dashboard/export/${format}`, '_blank');
        } catch (error) {
            console.error('Export error:', error);
            this.notification.add('Erreur lors de l\'export', { type: 'warning' });
        }
    }
    
    // Action methods remain the same...
    openCampaignsList() {
        try {
            const actionData = {
                type: 'ir.actions.act_window',
                name: 'Campagnes de Recrutement',
                res_model: 'ong.recruitment.campaign',
                view_mode: 'list,form',
                views: [[false, 'list'], [false, 'form']],
                target: 'current',
                domain: [],
                context: {}
            };
            
            this.actionService.doAction(actionData);
        } catch (error) {
            console.error('Error opening campaigns list:', error);
            this.notification.add('Erreur lors de l\'ouverture de la liste des campagnes', { type: 'warning' });
        }
    }
    
    openApplicationsList() {
        try {
            const actionData = {
                type: 'ir.actions.act_window',
                name: 'Candidatures',
                res_model: 'ong.application',
                view_mode: 'list,form',
                views: [[false, 'list'], [false, 'form']],
                target: 'current',
                domain: [],
                context: {}
            };
            
            this.actionService.doAction(actionData);
        } catch (error) {
            console.error('Error opening applications list:', error);
            this.notification.add('Erreur lors de l\'ouverture de la liste des candidatures', { type: 'warning' });
        }
    }

    // Add this method to your component class
    getAppStateColor(state) {
        const stateColors = {
            'draft': 'secondary',
            'submitted': 'info',
            'in_review': 'warning',
            'accepted': 'success',
            'rejected': 'danger',
            'pending': 'warning',
            'selected': 'success',
            'waiting': 'info',
            // Add more state mappings as needed
        };
        return stateColors[state] || 'secondary';
    }
    
    openApplication(applicationId) {
        try {
            if (!applicationId || isNaN(applicationId)) {
                throw new Error('ID de candidature invalide');
            }
            
            const actionData = {
                type: 'ir.actions.act_window',
                name: 'Candidature',
                res_model: 'ong.application',
                res_id: parseInt(applicationId),
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'current',
                context: {}
            };
            
            this.actionService.doAction(actionData);
        } catch (error) {
            console.error('Error opening application:', error);
            this.notification.add('Erreur lors de l\'ouverture de la candidature', { type: 'warning' });
        }
    }
    
    openCampaign(campaignId) {
        try {
            if (!campaignId || isNaN(campaignId)) {
                throw new Error('ID de campagne invalide');
            }
            
            const actionData = {
                type: 'ir.actions.act_window',
                name: 'Campagne',
                res_model: 'ong.recruitment.campaign',
                res_id: parseInt(campaignId),
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'current',
                context: {}
            };
            
            this.actionService.doAction(actionData);
        } catch (error) {
            console.error('Error opening campaign:', error);
            this.notification.add('Erreur lors de l\'ouverture de la campagne', { type: 'warning' });
        }
    }
    
    getStateColor(state) {
        const colors = {
            'draft': 'secondary',
            'submitted': 'info',
            'under_review': 'warning',
            'selected': 'success',
            'rejected': 'danger',
            'open': 'success',
            'evaluation': 'warning',
            'closed': 'secondary',
            'completed': 'primary',
            'in_progress': 'info',
            'canceled': 'warning',
            'closed': 'danger',
        };
        return colors[state] || 'secondary';
    }
    
    getInsightIcon(type) {
        const icons = {
            'success': 'fa-check-circle text-success',
            'warning': 'fa-exclamation-triangle text-warning',
            'info': 'fa-info-circle text-info',
            'danger': 'fa-times-circle text-danger'
        };
        return icons[type] || 'fa-info-circle text-info';
    }
    
    getPriorityColor(priority) {
        const priorityColors = {
            'high': 'danger',
            'medium': 'warning',
            'low': 'info',
            'critical': 'danger',
            'normal': 'success',
        };
        return priorityColors[priority.toLowerCase()] || 'secondary';
    }
    
    willUnmount() {
        try {
            const charts = [
                'statesChartInstance', 'countriesChartInstance', 'monthlyChartInstance',
                'scoreChartInstance', 'domainsChartInstance', 'trendsChartInstance', 'performanceChartInstance'
            ];
            
            charts.forEach(chartName => {
                if (this[chartName]) {
                    this[chartName].destroy();
                    this[chartName] = null;
                }
            });
        } catch (error) {
            console.error('Error cleaning up charts:', error);
        }
    }
}

registry.category('actions').add('ong_dashboard_widget', OngDashboardWidget);