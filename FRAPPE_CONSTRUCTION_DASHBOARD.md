# Construction Projects Dashboard (Frappe)

## Overview
A standard Frappe Dashboard has been created to monitor construction projects directly inside ERPNext. The dashboard uses built-in `Dashboard`, `Dashboard Chart`, and `Number Card` doctypes and can be managed entirely from Desk.

---

## Deploy / Refresh
1. Open the bench folder:
   ```bash
   cd /home/erp/frappe-bench
   ```
2. Apply fixtures to the target site:
   ```bash
   bench --site demo.shifa.ly migrate
   ```
3. Clear cache so the dashboard appears immediately:
   ```bash
   bench --site demo.shifa.ly clear-cache
   ```
Replace `demo.shifa.ly` with your own site name.

---

## Components

### Number Cards
- **Total Active Projects** – count of `Project` records with status *Open*
- **Total Project Value** – sum of `total_sales_amount`
- **Total Actual Cost** – sum of `total_costing_amount`
- **Total Gross Margin** – sum of `gross_margin`
- **Completed Tasks** – count of `Task` with status *Completed*
- **Overdue Tasks** – count of `Task` with status *Overdue*
- **Active Tasks** – count of `Task` with status *Open* or *Working*

### Dashboard Charts
| Chart | Type | Data |
|-------|------|------|
| Projects by Status | Donut / Group By | Distribution of projects by status |
| Tasks by Priority | Pie / Group By | Task distribution by priority |
| Monthly Project Sales | Bar / Sum | `total_sales_amount` per month |
| Monthly Project Costs | Bar / Sum | `total_costing_amount` per month |
| Project Gross Margin | Line / Sum | Monthly `gross_margin` trend |
| Monthly Completed Tasks | Line / Count | Tasks completed per month |

### Dashboard Definition
- **Name:** Construction Projects
- **Module:** Milestoneksa
- **Cards:** all KPIs above
- **Charts:** all charts above, each rendered at `Half` width pairs

---

## Access from Desk
1. Sign in as a user with dashboard permissions (System Manager, Projects Manager, etc.).
2. Use the global search (`Ctrl + K`) and type "Construction Projects".
3. Select the entry of type **Dashboard**.

Alternatively, open **Analytics → Dashboard** and choose **Construction Projects** from the list.

---

## Customising
- **Number Cards:** open the card record to adjust filters or aggregation.
- **Dashboard Charts:** tweak chart type, time window, colours, or filters.
- **Dashboard:** reorder cards/charts or change width directly from Desk.

All items are marked `is_standard = 1` and linked to the `Milestoneksa` module, so they can travel with the app fixtures.

---

## Verification Snippets
From bench console:
```python
frappe.db.exists("Dashboard", "Construction Projects")
frappe.get_all("Number Card", filters={"module": "Milestoneksa"}, pluck="name")
frappe.get_all("Dashboard Chart", filters={"module": "Milestoneksa"}, pluck="name")
```
Expect `True` and the lists of assets if fixtures loaded correctly.

---

## Move to Another Site
Fixtures are already declared in `hooks.py`:
```python
fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "Milestoneksa"]]},
    {"dt": "Number Card", "filters": [["module", "=", "Milestoneksa"]]},
    {"dt": "Dashboard Chart", "filters": [["module", "=", "Milestoneksa"]]},
    {"dt": "Dashboard", "filters": [["module", "=", "Milestoneksa"]]},
]
```
After installing the app on another site just run `bench --site <site> migrate`.

---

## Permissions
Users must have standard permissions to view dashboards and to read the underlying doctypes (`Project`, `Task`). No custom role changes are required.

---

## Notes
- Totals ignore projects with status *Cancelled*.
- Monthly sales/cost charts use the project `modified` timestamp; adjust if you need different timing logic.
- Completed tasks chart relies on the `completed_on` field being populated. Update tasks accordingly.
- Colours can be changed per chart by editing the record in Desk.

---

## Support
Questions or enhancements:
- 📧 ahmed@milestoneksa.com
- 📁 Dashboard assets live under `apps/milestoneksa/milestoneksa/milestoneksa/`

Enjoy real-time visibility into your construction portfolio! 🚀
