# -*- coding: utf-8 -*-
import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, add_days, get_first_day, get_last_day, now_datetime
from datetime import datetime, timedelta


@frappe.whitelist()
def get_dashboard_data(project: str, from_date=None, to_date=None):
    """Get comprehensive dashboard data for a project"""
    if not project:
        frappe.throw(_("Project is required"))
    
    project_doc = frappe.get_doc("Project", project)
    
    # Parse date filters
    if from_date:
        from_date = getdate(from_date)
    if to_date:
        to_date = getdate(to_date)
    
    # Get metrics with error handling
    try:
        financial = get_financial_metrics(project, project_doc)
    except Exception as e:
        frappe.log_error(f"Dashboard financial error: {str(e)}")
        financial = {}
    
    try:
        timeline = get_timeline_metrics(project, project_doc)
    except Exception as e:
        frappe.log_error(f"Dashboard timeline error: {str(e)}")
        timeline = {}
    
    try:
        tasks = get_task_metrics(project, from_date, to_date)
    except Exception as e:
        frappe.log_error(f"Dashboard tasks error: {str(e)}")
        tasks = {}
    
    try:
        team = get_team_metrics(project, from_date, to_date)
    except Exception as e:
        frappe.log_error(f"Dashboard team error: {str(e)}")
        team = {"team_size": 0, "total_hours": 0, "by_activity": {}, "users": []}
    
    try:
        trends = get_historical_trends(project, from_date, to_date)
    except Exception as e:
        frappe.log_error(f"Dashboard trends error: {str(e)}")
        trends = {"task_completion": [], "cost_trend": []}
    
    # Calculate overall project health score
    health_score = calculate_health_score(financial, timeline, tasks, team)
    
    return {
        "financial": financial,
        "timeline": timeline,
        "tasks": tasks,
        "team": team,
        "trends": trends,
        "health": health_score,
        "project_info": {
            "name": project_doc.name,
            "project_name": project_doc.project_name,
            "status": project_doc.status,
            "company": project_doc.company,
            "customer": project_doc.customer,
        }
    }


def calculate_health_score(financial, timeline, tasks, team):
    """Calculate overall project health score (0-100)"""
    score = 0
    
    # Budget Health (30 points)
    budget_score = 0
    if financial.get("budget_health") == "good":
        budget_score = 30
    elif financial.get("budget_health") == "warning":
        budget_score = 20
    elif financial.get("budget_health") == "danger":
        budget_score = 10
    else:
        budget_score = 15  # No budget set
    
    # Schedule Health (30 points)
    schedule_score = 0
    pct_complete = flt(timeline.get("percent_complete", 0))
    delay_days = flt(timeline.get("delay_days", 0))
    
    if timeline.get("status") == "on-track":
        schedule_score = 30
    elif delay_days <= 7:
        schedule_score = 20
    elif delay_days <= 30:
        schedule_score = 10
    else:
        schedule_score = 5
    
    # Task Health (25 points)
    task_score = 0
    completion_pct = flt(tasks.get("completion_pct", 0))
    overdue = cint(tasks.get("overdue", 0))
    total_tasks = cint(tasks.get("total", 1))
    
    task_score = int(completion_pct * 0.2)  # 20 points for completion
    if overdue == 0:
        task_score += 5  # 5 bonus points for no overdue
    elif overdue < (total_tasks * 0.1):
        task_score += 3  # Small number of overdue
    
    # Team Health (15 points)
    team_score = 0
    team_size = cint(team.get("team_size", 0))
    if team_size > 0:
        team_score = 10  # Has team assigned
        if team.get("total_hours", 0) > 0:
            team_score += 5  # Team is logging time
    
    total_score = budget_score + schedule_score + task_score + team_score
    
    # Determine health level
    if total_score >= 80:
        health_level = "excellent"
    elif total_score >= 60:
        health_level = "good"
    elif total_score >= 40:
        health_level = "warning"
    else:
        health_level = "danger"
    
    return {
        "score": total_score,
        "level": health_level,
        "components": {
            "budget": budget_score,
            "schedule": schedule_score,
            "tasks": task_score,
            "team": team_score
        }
    }


def get_financial_metrics(project: str, project_doc):
    """Calculate financial KPIs"""
    estimated_cost = flt(project_doc.estimated_costing)
    total_costing = flt(project_doc.total_costing_amount)
    total_purchase = flt(project_doc.total_purchase_cost)
    total_expense = flt(project_doc.get("total_expense_claim", 0))
    total_sales = flt(project_doc.total_sales_amount)
    total_billed = flt(project_doc.total_billed_amount)
    total_billable = flt(project_doc.total_billable_amount)
    
    actual_cost = total_costing + total_purchase + total_expense
    budget_variance = estimated_cost - actual_cost if estimated_cost else 0
    budget_variance_pct = (budget_variance / estimated_cost * 100) if estimated_cost else 0
    
    # Revenue metrics
    unbilled_revenue = total_sales - total_billed
    revenue_realization = (total_billed / total_sales * 100) if total_sales else 0
    
    # Profitability
    gross_profit = total_sales - actual_cost
    profit_margin_pct = (gross_profit / total_sales * 100) if total_sales else 0
    
    # Budget health
    if not estimated_cost:
        budget_health = "warning"  # No budget set
    elif budget_variance_pct >= 0:
        budget_health = "good"
    elif budget_variance_pct >= -10:
        budget_health = "warning"
    else:
        budget_health = "danger"
    
    return {
        "estimated_budget": estimated_cost,
        "actual_cost": actual_cost,
        "budget_variance": budget_variance,
        "budget_variance_pct": budget_variance_pct,
        "budget_health": budget_health,
        "total_revenue": total_sales,
        "total_billed": total_billed,
        "unbilled_revenue": unbilled_revenue,
        "revenue_realization_pct": revenue_realization,
        "gross_profit": gross_profit,
        "profit_margin_pct": profit_margin_pct,
        "gross_margin": flt(project_doc.gross_margin),
        "margin_pct": flt(project_doc.per_gross_margin),
        "breakdown": {
            "timesheet_cost": total_costing,
            "purchase_cost": total_purchase,
            "expense_claims": total_expense,
        }
    }


def get_timeline_metrics(project: str, project_doc):
    """Calculate timeline/schedule KPIs"""
    exp_start = project_doc.expected_start_date
    exp_end = project_doc.expected_end_date
    act_start = project_doc.actual_start_date
    act_end = project_doc.actual_end_date
    
    today = getdate()
    
    status = "on-track"
    delay_days = 0
    
    if exp_end:
        if act_end:
            # Project completed
            delay_days = (getdate(act_end) - getdate(exp_end)).days
        elif today > getdate(exp_end):
            # Project overdue
            delay_days = (today - getdate(exp_end)).days
            status = "delayed"
    
    # Calculate days remaining
    days_remaining = 0
    if exp_end and not act_end:
        days_remaining = (getdate(exp_end) - today).days
        if days_remaining < 0:
            days_remaining = 0
    
    # Milestone status
    milestones = frappe.get_all(
        "Task",
        filters={"project": project, "is_milestone": 1},
        fields=["name", "status", "exp_end_date"]
    )
    
    completed_milestones = len([m for m in milestones if m.status == "Completed"])
    total_milestones = len(milestones)
    
    return {
        "expected_start": exp_start,
        "expected_end": exp_end,
        "actual_start": act_start,
        "actual_end": act_end,
        "delay_days": delay_days,
        "status": status,
        "days_remaining": days_remaining,
        "percent_complete": flt(project_doc.percent_complete),
        "milestones": {
            "total": total_milestones,
            "completed": completed_milestones,
            "pending": total_milestones - completed_milestones,
        }
    }


def get_task_metrics(project: str, from_date=None, to_date=None):
    """Calculate task-related KPIs"""
    filters = {"project": project}
    
    all_tasks = frappe.get_all(
        "Task",
        filters=filters,
        fields=["name", "status", "priority", "exp_end_date", "is_group"]
    )
    
    # Count by status
    status_counts = {}
    for task in all_tasks:
        status = task.status or "Open"
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Count by priority
    priority_counts = {}
    for task in all_tasks:
        priority = task.priority or "Medium"
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    # Count overdue
    today = getdate()
    overdue = [t for t in all_tasks if t.exp_end_date and getdate(t.exp_end_date) < today and t.status not in ("Completed", "Cancelled")]
    
    completed = len([t for t in all_tasks if t.status == "Completed"])
    total = len(all_tasks)
    
    return {
        "total": total,
        "completed": completed,
        "pending": total - completed,
        "completion_pct": (completed / total * 100) if total else 0,
        "overdue": len(overdue),
        "by_status": status_counts,
        "by_priority": priority_counts,
        "overdue_tasks": [{"name": t.name, "exp_end_date": t.exp_end_date, "priority": t.priority} for t in overdue[:10]]
    }


def get_team_metrics(project: str, from_date=None, to_date=None):
    """Calculate team/resource metrics"""
    # Get project users
    users = frappe.get_all(
        "Project User",
        filters={"parent": project},
        fields=["user"]
    )
    
    # Get timesheet data
    timesheet_filters = {"project": project}
    
    timesheets = frappe.get_all(
        "Timesheet Detail",
        filters=timesheet_filters,
        fields=["hours", "parent", "activity_type"]
    )
    
    # Get user info from timesheets (owner)
    timesheet_by_user = {}
    for ts in timesheets:
        # Get parent timesheet to find owner
        parent_doc = frappe.get_cached_value("Timesheet", ts.parent, ["owner", "employee"], as_dict=True)
        if parent_doc:
            user = parent_doc.get("owner")
            hours = flt(ts.hours)
            
            if user not in timesheet_by_user:
                timesheet_by_user[user] = {
                    "hours": 0,
                    "activities": {}
                }
            
            timesheet_by_user[user]["hours"] += hours
            
            activity = ts.activity_type or "Other"
            timesheet_by_user[user]["activities"][activity] = \
                timesheet_by_user[user]["activities"].get(activity, 0) + hours
    
    total_hours = sum(flt(ts.hours) for ts in timesheets)
    
    # Hours by activity
    activity_hours = {}
    for ts in timesheets:
        activity = ts.activity_type or "Other"
        activity_hours[activity] = activity_hours.get(activity, 0) + flt(ts.hours)
    
    # Build user breakdown
    user_breakdown = []
    for user, data in timesheet_by_user.items():
        user_breakdown.append({
            "user": user,
            "hours": data["hours"],
            "activities": data["activities"]
        })
    
    # Sort by hours descending
    user_breakdown.sort(key=lambda x: x["hours"], reverse=True)
    
    return {
        "team_size": len(users),
        "total_hours": total_hours,
        "by_activity": activity_hours,
        "users": [u.user for u in users],
        "user_breakdown": user_breakdown
    }


def get_historical_trends(project: str, from_date=None, to_date=None):
    """Get historical trend data for charts"""
    
    # Default to last 3 months if no dates
    if not to_date:
        to_date = getdate()
    if not from_date:
        from_date = add_days(to_date, -90)
    
    # Get task completion trend (tasks completed per week)
    completed_tasks = frappe.get_all(
        "Task",
        filters={
            "project": project,
            "status": "Completed",
            "completed_on": ["between", [from_date, to_date]]
        },
        fields=["completed_on"],
        order_by="completed_on asc"
    )
    
    # Group by week
    weekly_completions = {}
    for task in completed_tasks:
        if task.completed_on:
            week_start = get_week_start(task.completed_on)
            weekly_completions[week_start] = weekly_completions.get(week_start, 0) + 1
    
    # Get cost trend from BOTH Purchase Invoices AND Expense Claims
    purchase_invoices = frappe.get_all(
        "Purchase Invoice Item",
        filters={
            "project": project,
            "docstatus": 1
        },
        fields=["parent", "amount"],
    )
    
    # Get parent Purchase Invoice dates
    pi_data = []
    for item in purchase_invoices:
        pi = frappe.db.get_value("Purchase Invoice", item.parent, ["posting_date"], as_dict=True)
        if pi and pi.posting_date:
            if not from_date or not to_date or (getdate(pi.posting_date) >= from_date and getdate(pi.posting_date) <= to_date):
                pi_data.append({
                    "date": pi.posting_date,
                    "amount": flt(item.amount)
                })
    
    # Get expense claims
    expense_claims = frappe.get_all(
        "Expense Claim",
        filters={
            "project": project,
            "docstatus": 1
        },
        fields=["posting_date", "total_claimed_amount"],
        order_by="posting_date asc"
    )
    
    # Combine and sort all costs by date
    all_costs = []
    for pi in pi_data:
        all_costs.append({"date": pi["date"], "amount": pi["amount"]})
    for exp in expense_claims:
        if not from_date or not to_date or (getdate(exp.posting_date) >= from_date and getdate(exp.posting_date) <= to_date):
            all_costs.append({"date": exp.posting_date, "amount": flt(exp.total_claimed_amount)})
    
    all_costs.sort(key=lambda x: getdate(x["date"]))
    
    # Cumulative cost trend
    cost_trend = []
    cumulative = 0
    for cost in all_costs:
        cumulative += flt(cost["amount"])
        cost_trend.append({
            "date": str(cost["date"]),
            "amount": cumulative
        })
    
    return {
        "task_completion": [{"week": str(k), "count": v} for k, v in sorted(weekly_completions.items())],
        "cost_trend": cost_trend,
    }


def get_week_start(date):
    """Get the Monday of the week for a given date"""
    date = getdate(date)
    return date - timedelta(days=date.weekday())


@frappe.whitelist()
def get_top_expenses(project: str, limit=10):
    """Get top expenses for the project"""
    expenses = frappe.get_all(
        "Expense Claim",
        filters={"project": project, "docstatus": 1},
        fields=["name", "employee_name", "total_claimed_amount", "posting_date", "expense_approver"],
        order_by="total_claimed_amount desc",
        limit=limit
    )
    
    return expenses

