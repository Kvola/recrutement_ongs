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
            error: null
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
    
    renderCharts() {
        setTimeout(() => {
            try {
                this.renderStatesChart();
                this.renderCountriesChart();
                this.renderMonthlyChart();
                this.renderScoreChart();
                this.renderDomainsChart();
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
                        '#6f42c1', '#17a2b8', '#28a745', 
                        '#fd7e14', '#dc3545', '#6c757d'
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 10,
                            font: {
                                size: 11
                            }
                        }
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
                    backgroundColor: '#3498db',
                    borderColor: '#2980b9',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            font: {
                                size: 10
                            }
                        }
                    },
                    x: {
                        ticks: {
                            font: {
                                size: 10
                            }
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
                    borderColor: '#27ae60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#27ae60',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            font: {
                                size: 10
                            }
                        }
                    },
                    x: {
                        ticks: {
                            font: {
                                size: 10
                            }
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
                        '#e74c3c', '#f39c12', '#f1c40f',
                        '#27ae60', '#16a085', '#3498db'
                    ],
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            font: {
                                size: 10
                            }
                        }
                    },
                    x: {
                        ticks: {
                            font: {
                                size: 10
                            }
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
                    backgroundColor: '#9b59b6',
                    borderColor: '#8e44ad',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            font: {
                                size: 10
                            }
                        }
                    },
                    y: {
                        ticks: {
                            font: {
                                size: 10
                            }
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
    
    // Fixed action methods with better error handling
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
    
    openSupport() {
        try {
            const actionData = {
                type: 'ir.actions.act_url',
                url: '/web/support',
                target: 'new'
            };
            
            this.actionService.doAction(actionData);
        } catch (error) {
            console.error('Error opening support:', error);
            this.notification.add('Page de support non disponible', { type: 'info' });
        }
    }
    
    openDocumentation() {
        try {
            const actionData = {
                type: 'ir.actions.act_url',
                url: '/web/documentation',
                target: 'new'
            };
            
            this.actionService.doAction(actionData);
        } catch (error) {
            console.error('Error opening documentation:', error);
            this.notification.add('Documentation non disponible', { type: 'info' });
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
            'closed': 'secondary'
        };
        return colors[state] || 'secondary';
    }
    
    // Enhanced cleanup method
    willUnmount() {
        try {
            if (this.statesChartInstance) {
                this.statesChartInstance.destroy();
                this.statesChartInstance = null;
            }
            if (this.countriesChartInstance) {
                this.countriesChartInstance.destroy();
                this.countriesChartInstance = null;
            }
            if (this.monthlyChartInstance) {
                this.monthlyChartInstance.destroy();
                this.monthlyChartInstance = null;
            }
            if (this.scoreChartInstance) {
                this.scoreChartInstance.destroy();
                this.scoreChartInstance = null;
            }
            if (this.domainsChartInstance) {
                this.domainsChartInstance.destroy();
                this.domainsChartInstance = null;
            }
        } catch (error) {
            console.error('Error cleaning up charts:', error);
        }
    }
}

// Register the component
registry.category('actions').add('ong_dashboard_widget', OngDashboardWidget);