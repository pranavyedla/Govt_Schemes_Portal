# Government Schemes Portal 🏛️

An online portal built with Flask and SQLAlchemy that allows users to browse, search, and manage information on government schemes. Designed for multilingual support via Flask-Babel.

---

## 🔍 Features

- **Browse & search** government schemes by name, category, or eligibility.
- **View scheme details**, including description, benefits, applying process.
- **Interactive chatbot**:
  - Ask questions in natural language (e.g., “What schemes are available for students?”).
  - Provides guided responses and scheme suggestions.
  - Powered by a fine-tuned Gemini API, enabling intelligent and context-aware responses.
- **Admin interface** (if applicable) for adding/editing/removing schemes.
- **Multilingual support** (English + other locales) using Flask-Babel.
- **Modular structure** with `app.py`, `models.py`, and `views.py`.
- **Database support** using SQLAlchemy with SQLite by default.

---

## 🧩 Project Structure

```
Govt_Schemes_Portal/
├── app.py            # Flask app initialization
├── models.py         # SQLAlchemy ORM models
├── views.py          # Routes and controllers
├── requirements.txt  # Python dependencies
├── templates/        # Jinja2 HTML templates
├── static/           # CSS, JavaScript, images
├── translations/     # Locale files for i18n
├── babel.cfg         # Translation configuration
├── messages.pot       # Translation template extraction
├── sql/              # SQL scripts or migrations
└── README.md         # (this file)
```

---

## 🚀 Getting Started

### 1. **Clone the repo**

```bash
git clone https://github.com/pranavyedla/Govt_Schemes_Portal.git
cd Govt_Schemes_Portal
```

### 2. **Set up a virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. **Install dependencies**

```bash
pip install -r requirements.txt
```

### 4. **Set environment variables**

```bash
export FLASK_APP=app.py
export FLASK_ENV=development   
```

On Windows (PowerShell):

```powershell
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "development"
```

### 5. **Initialize the database**

```bash
python
>>> from models import db
>>> from app import create_app
>>> app = create_app()
>>> app.app_context().push()
>>> db.create_all()
>>> exit()
```

### 6. **Run the app**

```bash
flask run
```

Visit `http://127.0.0.1:5000/` in your browser.

---

## 💾 Database Schema

| Field       | Type     | Description                            |
|------------|----------|----------------------------------------|
| `id`       | Integer  | Primary key, auto-incremented         |
| `title`    | String   | Scheme name                          |
| `description` | Text   | Full description                     |
| `category` | String   | Category (e.g. education, health)    |
| `eligibility` | Text  | Eligibility criteria                 |
| `benefits` | Text     | Details of scheme benefits           |

---

## 📬 Contact

For questions or feedback:

- **Maintainer**: Pranav Yedla  
- **Email**: pranavyedla2004@gmail.com  

---

## 🔗 Acknowledgments

- [Flask](https://flask.palletsprojects.com/) – Micro web framework  
- [SQLAlchemy](https://www.sqlalchemy.org/) – ORM library  
- [Flask-Babel](https://python-babel.github.io/flask-babel/) – i18n support
