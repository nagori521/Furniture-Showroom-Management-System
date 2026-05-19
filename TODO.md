# TODO - Manufacturing Orders dashboard & reporting

- [x] Extend ManufacturingOrdersService with analytics helpers (counts + pending/deliveries + low-stock alert queries + recent activity fetch)
- [x] Update dashboard_cards in inventory_app/templates/dashboard.html to show professional manufacturing analytics cards
- [x] Update inventory_app/routes/dashboard_routes.py to supply manufacturing metrics to the dashboard template
- [ ] Add new route + service methods for `Manufacturing Reports` with filters (date + status)
- [ ] Create template inventory_app/templates/manufacturing_reports.html implementing report table + quantity summaries with status color coding (green/yellow/red)
- [ ] Update sidebar/base navigation if needed to link to Manufacturing Reports
- [ ] Update static CSS (inventory_app/static/css/styles.css) with manufacturing card styles + status badges/colors for report rows
- [ ] Run a quick app sanity check (import routes/templates) to ensure no template/context errors


