# Campus Event Management System

A web-based campus event management application built with **Flask**, **Flask-SQLAlchemy**, and **MySQL**. It allows students to explore upcoming campus events, register for them, and provides administrators with a dashboard to manage events and track student registrations.

---

## 🛠️ Tech Stack

- **Backend:** Python 3, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF
- **Database:** MySQL 8.0 (connected via PyMySQL & Cryptography)
- **Frontend:** HTML5, Jinja2 templates, CSS, Bootstrap

---

## 🚀 Setup & Installation (For Collaborators)

Follow these steps to run the project on your computer:

### 1. Clone the Repository
```bash
git clone <repository-url>
cd <repository-folder>
```

### 2. Set Up a Python Virtual Environment
**On Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up the MySQL Database
1. Make sure your MySQL service is running.
2. Import the included database dump:
   ```bash
   mysql -u root -p -e "CREATE DATABASE campus_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   mysql -u root -p campus_db < campus_db.sql
   ```

### 5. Configure Environment Variables
1. Copy `.env.example` to create your own `.env` file:
   - **Windows:** `copy .env.example .env`
   - **macOS/Linux:** `cp .env.example .env`
2. Open `.env` and replace `YOUR_PASSWORD` with your local MySQL password:
   ```env
   DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/campus_db
   SECRET_KEY=dev-only-change-me
   ```
   *(Note: If your MySQL password contains special characters like `@`, URL-encode it, e.g., `@` becomes `%40`)*.

### 6. Run the Application
```bash
python app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 🔑 Default Administrator Credentials

- **Email:** `admin@college.com`
- **Password:** `admin123`
*(Admin can access the admin dashboard to add/edit/delete events and view attendees).*

---

## 📁 Project Structure

```text
├── app.py              # Main Flask application, routes, and SQLAlchemy models
├── requirements.txt    # Python dependencies
├── campus_db.sql       # MySQL database dump (tables + seed data)
├── .env.example        # Environment variable template
├── .gitignore          # Files ignored by git (venv, .env, caches)
├── templates/          # HTML templates (Jinja2)
├── static/             # Static files (CSS, images, JS)
└── README.md           # Project documentation
```
