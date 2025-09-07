# ZPredict - University Admission Prediction System

A Django-based web application that provides university admission predictions and career recommendations for Sri Lankan students based on their A/L results.

## Features

- **University Admission Predictions**: Predict admission chances based on Z-score, stream, district, and year
- **Career Recommendations**: Get career suggestions based on degree programs using ML models
- **AI-Powered Chat**: Interactive chat system for university-related queries from UGC handbook
- **Student Dashboard**: Save and manage prediction results
- **Admin Panel**: Upload and manage university documents

## Tech Stack

- **Backend**: Django 5.2.3, Django REST Framework
- **Frontend**: HTML, CSS, JavaScript
- **Database**: PostgresSQL
- **ML Libraries**: scikit-learn, pandas, numpy
- **AI/NLP**: HuggingFace Transformers, LangChain, FAISS,Gemini
- **Authentication**: JWT tokens

## Installation

### Prerequisites

- Python 3.8+
- pip
- Virtual environment (recommended)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Zpredict
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   
   # On Windows
   .venv\Scripts\activate
   
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   ```

5. **Run migrations**
   ```bash
   cd zpredict
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

The application will be available at `http://127.0.0.1:8000/`

## Project Structure

```
Zpredict/
├── zpredict/                 # Main Django project
│   ├── api/                  # API application
│   │   ├── careermodel/      # ML model files (*.pkl)
│   │   ├── models.py         # Database models
│   │   ├── views.py          # API endpoints
│   │   ├── ml_utils.py       # ML prediction utilities
│   │   └── careermodel_utils.py  # Career recommendation logic
│   ├── UI/                   # Frontend application
│   │   ├── templates/        # HTML templates
│   │   ├── static/           # CSS, JS, images
│   │   └── views.py          # Frontend views
│   ├── zpredict/            # Django settings
│   └── manage.py
├── requirements.txt
├── .gitignore
└── README.md
```

## API Endpoints

### Authentication
- `POST /api/register/` - Student registration
- `POST /api/login/` - Student login
- `POST /api/admin/login/` - Admin login

### Predictions
- `POST /api/predictions/` - Get university admission predictions
- `GET /api/predictions/history/` - Get prediction history
- `POST /api/predictions/save/` - Save specific predictions

### Career Recommendations
- `POST /api/recommendations/` - Get career recommendations

### Chat System
- `POST /api/chat/` - Interactive chat with AI

### Admin
- `POST /api/admin/upload/` - Upload university documents
- `GET /api/admin/dashboard/` - Admin dashboard data

## Usage

### For Students

1. **Register/Login**: Create an account or login
2. **Get Predictions**: Enter your Z-score, stream, district, and year
3. **Save Results**: Save interesting university/course combinations
4. **Career Guidance**: Get career recommendations based on degree programs
5. **Ask Questions**: Use the chat system for university-related queries

### For Admins

1. **Login**: Use admin credentials
2. **Upload Documents**: Upload university handbooks and documents
3. **Monitor System**: View dashboard with system statistics
4. **Manage Data**: Process and manage uploaded documents

## Machine Learning Models

The system uses several ML models:

- **Admission Prediction**: Predicts cutoff scores and selection probability
- **Career Recommendation**: TF-IDF based similarity matching with O*NET data
- **Document Processing**: FAISS vector store for document retrieval

Model files are stored in `api/careermodel/` and loaded automatically on server startup.

## Development

### Running Tests
```bash
python manage.py test
```

### Code Style
- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to functions and classes

### Adding New Features
1. Create feature branch
2. Implement changes
3. Add tests
4. Update documentation
5. Submit pull request

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For support or questions, please create an issue in the GitHub repository.
