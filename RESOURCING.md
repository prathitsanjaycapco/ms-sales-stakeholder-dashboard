# Resourcing operations

The resourcing lifecycle uses the same canonical project, Capco employee, Morgan Stanley stakeholder, and engagement-assignment records as the rest of the account application.

## Production import

Apply Alembic migrations first, then validate a JSON batch without writing it:

```powershell
python -m backend.manage import-resourcing --file .\resourcing-import.json --dry-run
```

Remove `--dry-run` to import. The file shape is:

```json
{
  "requirements": [
    {
      "source_id": "demand-1001",
      "pod_id": "ISG",
      "division_id": "isg-front-office",
      "business_unit_id": "isg-front-office-equities",
      "engagement_id": "eng-isg-equities",
      "title": "Senior Data Engineer",
      "role": "Data Engineer",
      "requested_headcount": 2,
      "level": "Principal Consultant",
      "location": "New York",
      "required_skills": ["Python", "Data Engineering"],
      "preferred_skills": ["AWS"],
      "target_start_date": "2026-10-01",
      "priority": "HIGH",
      "status": "OPEN",
      "request_owner_capco_employee_id": "capco-employee-id",
      "client_stakeholder_id": "ms-stakeholder-id"
    }
  ],
  "candidates": [
    {
      "source_id": "candidate-1001",
      "resource_requirement_id": "demand-1001",
      "candidate_type": "EXTERNAL",
      "first_name": "Alex",
      "last_name": "Taylor",
      "email": "alex.taylor@example.com",
      "level": "Principal Consultant",
      "location": "New York",
      "skills": ["Python", "Data Engineering"],
      "stage": "IDENTIFIED",
      "capco_reviewer_id": "capco-employee-id",
      "ms_reviewer_stakeholder_id": "ms-stakeholder-id",
      "match_score": 85
    }
  ]
}
```

`source_id` lets candidates reference requirements created in the same batch. Canonical engagement, employee, and stakeholder IDs are validated during the live import. Mutations through the API are audited, commercial rates are restricted to Account Manager/Admin roles, and update endpoints accept `expected_updated_at` to reject stale writes.
