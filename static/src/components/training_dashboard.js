/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class TrainingDashboard extends Component {
    static template = "employee_training.TrainingDashboard";

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            upcomingSessions: [],
            expiringCertificates: [],
            topCourses: [],
            enrollmentsPerMonth: [],
            statistics: {},
            isLoading: true,
            showEnrollmentDialog: false,
            availableSessions: [],
            availableEmployees: [],
            selectedEmployee: null,
            selectedSession: null,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.isLoading = true;
        try {
            // Call the controller method directly using ORM execute_kw
            const data = await this.orm.call(
                "training.session",
                "get_dashboard_data",
                []
            );
            
            this.state.upcomingSessions = data.upcoming_sessions;
            this.state.expiringCertificates = data.expiring_certificates;
            this.state.topCourses = data.top_courses;
            this.state.enrollmentsPerMonth = data.enrollments_per_month;
            this.state.statistics = data.statistics;
            
            // Render chart after data is loaded
            setTimeout(() => this.renderChart(), 100);
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.notification.add(_t("Error loading dashboard data"), {
                type: "danger",
            });
        } finally {
            this.state.isLoading = false;
        }
    }

    renderChart() {
        const canvas = document.getElementById("enrollmentsChart");
        if (!canvas) return;

        // Check if Chart.js is available
        if (typeof Chart === 'undefined') {
            console.warn("Chart.js is not loaded. Chart will not be rendered.");
            return;
        }

        const ctx = canvas.getContext("2d");
        
        // Destroy existing chart if any
        if (this.chart) {
            this.chart.destroy();
        }

        // Prepare data
        const labels = this.state.enrollmentsPerMonth.map(d => d.month);
        const confirmedData = this.state.enrollmentsPerMonth.map(d => d.confirmed);
        const attendedData = this.state.enrollmentsPerMonth.map(d => d.attended);
        const cancelledData = this.state.enrollmentsPerMonth.map(d => d.cancelled);

        // Create chart using Chart.js
        this.chart = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Confirmed",
                        data: confirmedData,
                        borderColor: "#3498db",
                        backgroundColor: "rgba(52, 152, 219, 0.1)",
                        tension: 0.4,
                        fill: true,
                    },
                    {
                        label: "Attended",
                        data: attendedData,
                        borderColor: "#2ecc71",
                        backgroundColor: "rgba(46, 204, 113, 0.1)",
                        tension: 0.4,
                        fill: true,
                    },
                    {
                        label: "Cancelled",
                        data: cancelledData,
                        borderColor: "#e74c3c",
                        backgroundColor: "rgba(231, 76, 60, 0.1)",
                        tension: 0.4,
                        fill: true,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "top",
                    },
                    title: {
                        display: true,
                        text: "Enrollments Trend (Last 12 Months)",
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                        },
                    },
                },
            },
        });
    }

    async openSessionRecord(sessionId) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "training.session",
            res_id: sessionId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openCertificateRecord(certId) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "training.certificate",
            res_id: certId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openCourseRecord(courseId) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "training.course",
            res_id: courseId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openQuickEnrollDialog() {
        this.state.isLoading = true;
        try {
            const sessions = await this.orm.call(
                "training.session",
                "get_available_sessions",
                []
            );
            
            const employees = await this.orm.searchRead(
                "hr.employee",
                [],
                ["id", "name"],
                { order: "name" }
            );
            
            this.state.availableSessions = sessions;
            this.state.availableEmployees = employees;
            this.state.showEnrollmentDialog = true;
        } catch (error) {
            console.error("Error loading enrollment data:", error);
            this.notification.add(_t("Error loading enrollment data"), {
                type: "danger",
            });
        } finally {
            this.state.isLoading = false;
        }
    }

    closeEnrollmentDialog() {
        this.state.showEnrollmentDialog = false;
        this.state.selectedEmployee = null;
        this.state.selectedSession = null;
    }

    onEmployeeChange(ev) {
        this.state.selectedEmployee = parseInt(ev.target.value);
    }

    onSessionChange(ev) {
        this.state.selectedSession = parseInt(ev.target.value);
    }

    async createEnrollment() {
        if (!this.state.selectedEmployee || !this.state.selectedSession) {
            this.notification.add(_t("Please select both employee and session"), {
                type: "warning",
            });
            return;
        }

        try {
            // Create enrollment using ORM
            const enrollmentId = await this.orm.create(
                "training.enrollment",
                [{
                    employee_id: this.state.selectedEmployee,
                    session_id: this.state.selectedSession,
                }]
            );
            
            // Confirm the enrollment
            await this.orm.call(
                "training.enrollment",
                "action_confirm",
                [[enrollmentId]]
            );
            
            this.notification.add(_t("Enrollment created and confirmed successfully"), {
                type: "success",
            });
            
            this.closeEnrollmentDialog();
            // Refresh dashboard data
            await this.loadDashboardData();
        } catch (error) {
            this.notification.add(_t("Error creating enrollment: ") + error.message, {
                type: "danger",
            });
            console.error("Error:", error);
        }
    }

    getProgressBarColor(percentage) {
        if (percentage >= 80) return "bg-success";
        if (percentage >= 50) return "bg-warning";
        return "bg-danger";
    }

    getDaysColor(days) {
        if (days <= 7) return "text-danger fw-bold";
        if (days <= 15) return "text-warning fw-bold";
        return "text-muted";
    }
}

// Register the component as an action
registry.category("actions").add("training_dashboard", TrainingDashboard);