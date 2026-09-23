# Governed executive-data import

Delivery, revenue, milestone, capacity, and allocation records should arrive from approved source systems rather than ad-hoc browser edits. Apply migrations, validate a batch, then import it transactionally:

```powershell
python -m app.manage import-executive --file .\executive-import.json --dry-run
python -m app.manage import-executive --file .\executive-import.json
```

Every referenced pod, division, business unit, stakeholder, opportunity, employee, and engagement must already exist or be included in the engagement portion of the same batch. IDs are stable upsert keys. Engagement `source_system` and `source_record_id` identify the upstream record and the import records its synchronization time.

```json
{
  "engagements": [{
    "id": "eng-risk-modernization",
    "pod_id": "ISG",
    "division_id": "isg-front-office",
    "business_unit_id": "isg-front-office-equities",
    "division": "Institutional Securities",
    "business_unit": "Equities",
    "name": "Risk modernization",
    "health": "AMBER",
    "status": "Active",
    "commercial_value": 2500000,
    "quarterly_revenue_target": 625000,
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "renewal_date": "2026-11-15",
    "executive_sponsor_id": null,
    "opportunity_id": null,
    "source_system": "approved-psa",
    "source_record_id": "project-1042"
  }],
  "milestones": [{
    "id": "milestone-1042-design",
    "engagement_id": "eng-risk-modernization",
    "title": "Design approval",
    "due_date": "2026-09-15",
    "status": "On Track",
    "completed_date": null
  }],
  "revenue_records": [{
    "id": "revenue-1042-2026-08",
    "engagement_id": "eng-risk-modernization",
    "recognized_on": "2026-08-31",
    "amount": 210000
  }],
  "capacity": [],
  "assignments": []
}
```

Run `/api/integrity/reconciliation` after every production import. An external scheduler should provide its own run identity, preserve source IDs, retry the same file safely, and alert when freshness becomes stale.
