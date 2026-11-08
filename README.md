# CampusFind – Campus Lost and Found Portal

CampusFind is a Flask and MySQL web application that allows students to report lost/found items, browse and filter reports, contact reporters through private messages, and manage their own reports. Administrators can manage user roles and remove inappropriate reports.

## Requirements
- Python 3.10 or later
- MySQL Server
- MySQL Workbench (optional)
- VS Code (optional)

## 1. Create the database
Open MySQL Workbench and run `database/schema.sql`. This creates `campusfind_db`, the four tables, and default categories.

## 2. Set up Python
Open a terminal in the CampusFind project folder:

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Configure database credentials
Copy `.env.example` to `.env`. Set DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME and a strong SECRET_KEY. Do not share or commit `.env`.

## 4. Initialise tables/categories
The schema SQL already creates the tables. Alternatively, after configuring `.env`, run:

```powershell
flask --app app init-db
```

## 5. Start the application

```powershell
python app.py
```

Open http://127.0.0.1:5000

## 6. Create an administrator
First register a normal account through the website. Then run this SQL in MySQL Workbench, replacing the email with that account's email:

```sql
USE campusfind_db;
UPDATE users SET role = 'admin' WHERE email = 'your-admin-email@example.com';
```

Log out and log in again so Flask-Login reloads the account role. The Admin link will appear in the navigation bar.

## Main features
- Student registration, login and logout
- Report lost/found items with optional photograph
- Browse active reports
- Search by keyword and filter by type, category and location
- Item details and private messages to the reporter
- Inbox with read/unread status
- My Reports and status management (active, returned, closed)
- Admin dashboard, role management and report deletion

## Notes before deployment
This project is a college demonstration baseline, not a production-hardened service. Before exposing it publicly, add CSRF protection (Flask-WTF), email verification, rate limiting, secure HTTPS cookies, stronger admin provisioning, database backups, and cloud object storage for uploaded images. Set `debug=False` in production and use a production WSGI server such as Gunicorn.
