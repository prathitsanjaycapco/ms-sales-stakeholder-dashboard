STAKEHOLDER DASHBOARD - PORTABLE WINDOWS PACKAGE

No Python, Node.js, Docker, or installer is required on the recipient computer.

FIRST USE
1. Extract the entire StakeholderDashboard folder to Documents or another writable folder.
2. Prepare data\import.json using data\import-template.json as the contract.
3. Double-click ValidateData.cmd. Fix every reported error before continuing.
4. Double-click ImportData.cmd. A successful import creates data\dashboard.db.
5. Double-click StartDashboard.cmd. Keep its window open while using the dashboard.

UPDATING DATA
1. Close the running dashboard.
2. Replace data\import.json with the corrected complete dataset.
3. Run ValidateData.cmd and then ImportData.cmd.
4. Each replacement saves the previous database in data\backups.

BACKUP AND TRANSFER
The data folder contains the SQLite database, uploaded documents, and database backups.
Copy the entire StakeholderDashboard folder to move the application and its data together.

SECURITY
The application listens only on this computer at 127.0.0.1 and uses local development identity.
The executable is unsigned unless your organization signs it after building. Windows or endpoint
security may require IT approval before it can run.
