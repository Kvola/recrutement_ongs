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
            // Use a more reliable CDN or local Chart.js
            // Option 1: Try multiple CDNs as fallback
            await this.loadChartJSWithFallback();
            
            // Load local CSS
            await loadCSS('/recrutement_ongs/static/src/css/dashboard.css');
        } catch (error) {
            console.error('Failed to load Chart.js:', error);
            this.notification.add('Impossible de charger la bibliothèque de graphiques', { type: 'warning' });
        }
    }
    
    async loadChartJSWithFallback() {
        const cdnUrls = [
            // Try local first if available
            '/recrutement_ongs/static/lib/chart.js/chart.umd.js',
            // Fallback CDNs
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
        
        // If all CDNs fail, provide a fallback or disable charts
        throw new Error('Could not load Chart.js from any source');
    }
    
    async loadDashboardData() {
        try {
            this.state.loading = true;
            this.state.error = null;
            
            const result = await this.rpc('/ong/dashboard/data', {});
            
            if (result.error) {
                this.state.error = result.error;
                this.notification.add('Erreur lors du chargement des données', { type: 'danger' });
            } else {
                this.state.data = result;
                // Only render charts if Chart.js is available
                if (typeof Chart !== 'undefined') {
                    this.renderCharts();
                } else {
                    this.notification.add('Les graphiques ne peuvent pas être affichés', { type: 'info' });
                }
            }
        } catch (error) {
            console.error('Dashboard data loading error:', error);
            this.state.error = error.message;
            this.notification.add('Erreur de connexion au serveur', { type: 'danger' });
        } finally {
            this.state.loading = false;
        }
    }
    
    renderCharts() {
        // Add a small delay to ensure DOM is ready
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
        
        // Destroy existing chart if it exists
        if (this.statesChartInstance) {
            this.statesChartInstance.destroy();
        }
        
        this.statesChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: this.state.data.charts.applications_by_state.labels,
                datasets: [{
                    data: this.state.data.charts.applications_by_state.data,
                    backgroundColor: [
                        '#6f42c1', '#17a2b8', '#28a745', 
                        '#fd7e14', '#dc3545', '#6c757d'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Candidatures par État'
                    },
                    legend: {
                        position: 'bottom'
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
        
        this.countriesChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: this.state.data.charts.applications_by_country.labels,
                datasets: [{
                    label: 'Candidatures',
                    data: this.state.data.charts.applications_by_country.data,
                    backgroundColor: '#007bff',
                    borderColor: '#0056b3',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Top 5 Pays'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
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
        
        this.monthlyChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.state.data.charts.monthly_applications.labels,
                datasets: [{
                    label: 'Candidatures',
                    data: this.state.data.charts.monthly_applications.data,
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Évolution Mensuelle'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
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
        
        this.scoreChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: this.state.data.charts.score_distribution.labels,
                datasets: [{
                    label: 'Nombre d\'ONGs',
                    data: this.state.data.charts.score_distribution.data,
                    backgroundColor: [
                        '#dc3545', '#fd7e14', '#ffc107',
                        '#28a745', '#20c997', '#17a2b8'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Distribution des Scores'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
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
        
        // Note: Chart.js v4 doesn't have 'horizontalBar', use 'bar' with indexAxis: 'y'
        this.domainsChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: this.state.data.charts.top_activity_domains.labels,
                datasets: [{
                    label: 'Candidatures',
                    data: this.state.data.charts.top_activity_domains.data,
                    backgroundColor: '#6f42c1',
                    borderColor: '#5a2d91',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y', // This creates horizontal bars
                plugins: {
                    title: {
                        display: true,
                        text: 'Domaines d\'Activité Populaires'
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
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
        window.open(`/ong/dashboard/export/${format}`, '_blank');
    }
    
    openCampaignsList() {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Campagnes de Recrutement',
            res_model: 'ong.recruitment.campaign',
            view_mode: 'list,form',
            target: 'current',
        });
    }
    
    openApplicationsList() {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Candidatures',
            res_model: 'ong.application',
            view_mode: 'list,form',
            target: 'current',
        });
    }
    
    openApplication(applicationId) {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Candidature',
            res_model: 'ong.application',
            res_id: applicationId,
            view_mode: 'form',
            target: 'current',
        });
    }
    
    openCampaign(campaignId) {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Campagne',
            res_model: 'ong.recruitment.campaign',
            res_id: campaignId,
            view_mode: 'form',
            target: 'current',
        });
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
    
    // Cleanup method to destroy charts when component is destroyed
    willUnmount() {
        if (this.statesChartInstance) this.statesChartInstance.destroy();
        if (this.countriesChartInstance) this.countriesChartInstance.destroy();
        if (this.monthlyChartInstance) this.monthlyChartInstance.destroy();
        if (this.scoreChartInstance) this.scoreChartInstance.destroy();
        if (this.domainsChartInstance) this.domainsChartInstance.destroy();
    }
}

// Register the component
registry.category('actions').add('ong_dashboard_widget', OngDashboardWidget);