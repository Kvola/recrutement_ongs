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
        await loadJS('https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js');
        await loadCSS('/recrutement_ongs/static/src/css/dashboard.css');
    }
    
    async loadDashboardData() {
        try {
            this.state.loading = true;
            const result = await this.rpc('/ong/dashboard/data', {});
            
            if (result.error) {
                this.state.error = result.error;
                this.notification.add('Erreur lors du chargement des données', { type: 'danger' });
            } else {
                this.state.data = result;
                this.renderCharts();
            }
        } catch (error) {
            this.state.error = error.message;
            this.notification.add('Erreur de connexion', { type: 'danger' });
        } finally {
            this.state.loading = false;
        }
    }
    
    renderCharts() {
        setTimeout(() => {
            this.renderStatesChart();
            this.renderCountriesChart();
            this.renderMonthlyChart();
            this.renderScoreChart();
            this.renderDomainsChart();
        }, 100);
    }
    
    renderStatesChart() {
        const ctx = document.getElementById('statesChart');
        if (!ctx || !this.state.data.charts) return;
        
        new Chart(ctx, {
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
        if (!ctx || !this.state.data.charts) return;
        
        new Chart(ctx, {
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
        if (!ctx || !this.state.data.charts) return;
        
        new Chart(ctx, {
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
        if (!ctx || !this.state.data.charts) return;
        
        new Chart(ctx, {
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
        if (!ctx || !this.state.data.charts) return;
        
        new Chart(ctx, {
            type: 'horizontalBar',
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
}

// Register the component in multiple registries to ensure it's found
registry.category('actions').add('ong_dashboard_widget', OngDashboardWidget);
registry.category('dashboard_widgets').add('ong_dashboard_widget', OngDashboardWidget);