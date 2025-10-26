# ZPredict - University Admission Prediction System

A comprehensive Django-based web application that provides university admission predictions and career recommendations for Sri Lankan students based on their A/L results. The system features a complete admin management interface with user account management capabilities.

## Features

### 🎓 Student Features
- **University Admission Predictions**: Predict admission chances based on Z-score, stream, district, and year
- **Career Recommendations**: Get career suggestions based on degree programs using ML models
- **AI-Powered Chat**: Interactive chat system for university-related queries powered by Gemini AI
- **Student Dashboard**: Save and manage prediction results with comprehensive statistics
- **Profile Management**: Edit personal information and manage account settings
- **Prediction History**: View and manage all previous predictions
- **Saved Predictions**: Save and organize favorite university/course combinations

### 👨‍💼 Admin Features
- **Document Management**: Upload and manage university handbooks and documents
- **Admin Dashboard**: Comprehensive dashboard with system statistics and analytics
- **Account Management**: Manage all student and admin accounts with full CRUD operations
- **Admin Profile Management**: Edit admin details, change passwords, and manage account settings
- **User Analytics**: View detailed analytics on user registrations, predictions, and system usage
- **Feedback Management**: Monitor and manage student feedback
- **System Monitoring**: Real-time system health monitoring and model status
- **Soft Delete System**: Safe account deactivation with data preservation

## Tech Stack

- **Backend**: Django 5.2.3, Django REST Framework
- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Font Awesome Icons
- **Database**: SQLite (development), PostgreSQL (production ready)
- **ML Libraries**: scikit-learn, pandas, numpy, pickle
- **AI/NLP**: HuggingFace Transformers, LangChain, FAISS, Google Gemini AI
- **Authentication**: JWT tokens with refresh token support
- **Task Queue**: Celery with Redis (for background processing)
- **File Storage**: Django FileField with PDF processing
- **UI Framework**: Custom responsive design with glassmorphism effects

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
   GEMINI_API_KEY=your-gemini-api-key-here
   CELERY_BROKER_URL=redis://localhost:6379/0
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

7. **Start Celery worker (for background tasks)**
   ```bash
   # In a separate terminal
   celery -A zpredict worker --loglevel=info
   ```

8. **Run the development server**
   ```bash
   python manage.py runserver
   ```

The application will be available at `http://127.0.0.1:8000/`

### Quick Start Scripts

For Windows users, use the provided batch files:
- `start_services.bat` - Starts both Django server and Celery worker
- `start_celery.bat` - Starts only Celery worker
- `fix_network.bat` - Network troubleshooting script

## Project Structure

```
Zpredict/
├── zpredict/                 # Main Django project
│   ├── api/                  # API application
│   │   ├── careermodel/      # ML model files (*.pkl)
│   │   ├── ml_model/         # Additional ML models
│   │   ├── models.py         # Database models
│   │   ├── views.py          # API endpoints
│   │   ├── serializers.py    # DRF serializers
│   │   ├── ml_utils.py       # ML prediction utilities
│   │   ├── careermodel_utils.py  # Career recommendation logic
│   │   ├── tasks.py          # Celery background tasks
│   │   └── utils.py          # Utility functions
│   ├── UI/                   # Frontend application
│   │   ├── templates/        # HTML templates
│   │   │   ├── admin-dashboard.html
│   │   │   ├── adminprofile.html
│   │   │   ├── Manage.html
│   │   │   └── navbar.html
│   │   ├── static/           # CSS, JS, images
│   │   │   ├── css/          # Stylesheets
│   │   │   └── js/           # JavaScript files
│   │   ├── views.py          # Frontend views
│   │   └── urls.py           # URL routing
│   ├── website/              # Student-facing application
│   │   ├── templates/        # Student templates
│   │   ├── static/           # Student assets
│   │   ├── views.py          # Student views
│   │   └── urls.py           # Student URLs
│   ├── media/                # File uploads
│   │   ├── ugc_pdfs/         # Uploaded PDFs
│   │   └── vectorstores/     # FAISS vector stores
│   ├── zpredict/            # Django settings
│   │   ├── settings.py       # Main settings
│   │   ├── celery.py         # Celery configuration
│   │   └── urls.py           # Main URL routing
│   └── manage.py
├── requirements.txt
├── start_services.bat        # Windows startup script
├── start_celery.bat          # Celery startup script
├── fix_network.bat           # Network troubleshooting
├── .gitignore
└── README.md
```

## API Endpoints

### Authentication & User Management
- `POST /api/register/` - Student registration
- `POST /api/login/` - Student login
- `POST /api/admin/login/` - Admin login
- `POST /api/admin/register/` - Admin registration
- `GET /api/auth/me/` - Get current user profile
- `PUT /api/auth/update-profile/` - Update user profile
- `POST /api/auth/change-password/` - Change password
- `POST /api/auth/deactivate-account/` - Deactivate account
- `DELETE /api/auth/delete-account/` - Delete account

### Predictions
- `POST /api/predictions/` - Get university admission predictions
- `GET /api/prediction-sessions/` - Get prediction history
- `POST /api/predictions/save/` - Save specific predictions
- `GET /api/saved-predictions/` - Get saved predictions

### Career Recommendations
- `POST /api/recommendations/` - Get career recommendations
- `GET /api/career-sessions/` - Get career session history
- `GET /api/career-predictions/` - Get saved career predictions

### Chat System
- `POST /api/chat/` - Interactive chat with AI
- `GET /api/chat-history/` - Get chat history

### Admin Management
- `POST /api/admin/upload/` - Upload university documents
- `GET /api/admin/dashboard/` - Admin dashboard data
- `GET /api/admin/verify/` - Verify admin status
- `POST /api/admin/reprocess-pdf/` - Reprocess PDF documents

### User Management (Admin Only)
- `GET /api/users/` - List all users (with filtering)
- `GET /api/users/{id}/` - Get specific user
- `PATCH /api/users/{id}/` - Update user details
- `POST /api/users/{id}/restore_account/` - Restore deactivated account

### Analytics (Admin Only)
- `GET /api/admin/analytics/predictions/` - Prediction analytics
- `GET /api/admin/analytics/careers/` - Career recommendation analytics
- `GET /api/admin/analytics/users/` - User registration analytics

### System Monitoring
- `GET /api/models/status/` - Check ML model and system status

## Usage

### For Students

1. **Register/Login**: Create an account or login with your credentials
2. **Get Predictions**: Enter your Z-score, stream, district, and year to get admission predictions
3. **Save Results**: Save interesting university/course combinations for future reference
4. **Career Guidance**: Get career recommendations based on degree programs using ML models
5. **Ask Questions**: Use the AI-powered chat system for university-related queries
6. **Manage Profile**: Edit personal information and change password
7. **View History**: Access your prediction and career recommendation history
8. **Dashboard**: View comprehensive statistics and recent activity

### For Admins

1. **Login**: Use admin credentials to access the admin panel
2. **Dashboard**: View comprehensive system statistics and analytics
3. **Upload Documents**: Upload university handbooks and documents for AI processing
4. **Account Management**: 
   - View all student and admin accounts
   - Edit account details and status
   - Activate/deactivate accounts
   - Search and filter accounts
5. **Profile Management**: 
   - Edit admin profile information
   - Change password
   - Manage account settings
6. **System Monitoring**: 
   - Monitor ML model status
   - Check system health
   - View processing queues
7. **Analytics**: Access detailed analytics on user behavior and system usage
8. **Feedback Management**: Monitor and respond to student feedback

## Machine Learning Models

The system uses several ML models for different functionalities:

### 🎯 Admission Prediction Models
- **Regressor Model**: Predicts cutoff scores for university courses
- **Classifier Model**: Determines selection probability
- **Feature Encoder**: Encodes categorical features (stream, district, etc.)
- **Classifier Encoder**: Encodes classification features
- **Valid Courses Map**: Maps available courses to streams

### 🚀 Career Recommendation Models
- **TF-IDF Vectorizer**: Processes degree program text for similarity matching
- **Hybrid DataFrame**: Combined O*NET and Sri Lankan occupation data
- **Occupation DataFrame**: Sri Lankan occupation information
- **Similarity Engine**: Cosine similarity matching for career recommendations

### 📄 Document Processing
- **FAISS Vector Store**: Efficient similarity search for document retrieval
- **HuggingFace Embeddings**: Sentence transformers for text embeddings
- **LangChain Integration**: Document processing and retrieval chains

### 🤖 AI Chat System
- **Google Gemini AI**: Primary AI model for chat responses
- **HuggingFace T5**: Fallback model for text generation
- **Context Retrieval**: RAG (Retrieval-Augmented Generation) system

Model files are stored in `api/careermodel/` and `api/ml_model/` directories and are loaded automatically on server startup with caching for optimal performance.

## Development

### Running Tests
```bash
python manage.py test
```

### Code Style
- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to functions and classes
- Use type hints where appropriate

### Database Management
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load sample data (if available)
python manage.py loaddata fixtures/sample_data.json
```

### Background Tasks
```bash
# Start Celery worker
celery -A zpredict worker --loglevel=info

# Start Celery beat (for scheduled tasks)
celery -A zpredict beat --loglevel=info

# Monitor Celery tasks
celery -A zpredict flower
```

### Adding New Features
1. Create feature branch from main
2. Implement changes with proper error handling
3. Add comprehensive tests
4. Update API documentation
5. Update this README if needed
6. Submit pull request with detailed description

### Debugging
- Use Django Debug Toolbar in development
- Check Celery logs for background task issues
- Monitor ML model loading in server logs
- Use browser developer tools for frontend debugging

## Deployment

### Production Checklist

1. **Environment Configuration**
   - Set `DEBUG=False` in settings
   - Configure proper database (PostgreSQL recommended)
   - Set up Redis for Celery broker
   - Configure proper `ALLOWED_HOSTS`
   - Set up environment variables securely

2. **Database Setup**
   ```bash
   # Install PostgreSQL
   sudo apt-get install postgresql postgresql-contrib
   
   # Create database and user
   sudo -u postgres psql
   CREATE DATABASE zpredict_prod;
   CREATE USER zpredict_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE zpredict_prod TO zpredict_user;
   ```

3. **Static Files & Media**
   ```bash
   # Collect static files
   python manage.py collectstatic
   
   # Configure media file serving (use cloud storage for production)
   ```

4. **Web Server Configuration**
   - Use Gunicorn as WSGI server
   - Configure Nginx as reverse proxy
   - Set up SSL/HTTPS certificates
   - Configure proper headers and security

5. **Background Services**
   ```bash
   # Start Celery worker
   celery -A zpredict worker --loglevel=info --detach
   
   # Start Celery beat for scheduled tasks
   celery -A zpredict beat --loglevel=info --detach
   ```

6. **Monitoring & Logging**
   - Set up application monitoring (Sentry recommended)
   - Configure log rotation
   - Monitor system resources
   - Set up health checks

### Docker Deployment (Optional)
```dockerfile
# Example Dockerfile structure
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "zpredict.wsgi:application"]
```

### Cloud Deployment
- **AWS**: Use Elastic Beanstalk or ECS
- **Google Cloud**: Use App Engine or Cloud Run
- **Azure**: Use App Service
- **Heroku**: Use Heroku Postgres and Redis add-ons

## Security Features

- **JWT Authentication**: Secure token-based authentication with refresh tokens
- **CSRF Protection**: Cross-site request forgery protection
- **Input Validation**: Comprehensive input validation and sanitization
- **Soft Delete**: Safe account deactivation preserving data integrity
- **Permission System**: Role-based access control (Admin/Student)
- **Secure File Upload**: PDF validation and secure file handling
- **API Rate Limiting**: Protection against abuse and DDoS attacks

## Performance Optimizations

- **Model Caching**: ML models are cached in memory for faster predictions
- **Database Optimization**: Efficient queries with select_related and prefetch_related
- **Background Processing**: Celery for handling time-intensive tasks
- **Static File Optimization**: Minified CSS/JS and optimized images
- **API Pagination**: Efficient data loading with pagination support
- **Vector Store Caching**: FAISS vector stores cached for document retrieval

## Contributing

We welcome contributions to ZPredict! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** with proper documentation
4. **Add tests** for new functionality
5. **Update documentation** including this README
6. **Submit a pull request** with a detailed description

### Contribution Guidelines
- Follow PEP 8 style guidelines
- Write comprehensive tests for new features
- Update API documentation for new endpoints
- Ensure all tests pass before submitting
- Use meaningful commit messages

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, questions, or feature requests:
- Create an issue in the GitHub repository
- Check existing issues and discussions
- Review the documentation and API endpoints

## Acknowledgments

- **Sri Lankan University System**: For providing admission data and requirements
- **O*NET Database**: For career and occupation information
- **HuggingFace**: For pre-trained models and transformers
- **Google Gemini**: For AI-powered chat capabilities
- **Django Community**: For the excellent web framework
- **Open Source Contributors**: For various libraries and tools used

## Changelog

### Version 2.0.0 (Current)
- ✅ Complete admin management system
- ✅ User account management with CRUD operations
- ✅ Admin profile management
- ✅ Advanced analytics and reporting
- ✅ Enhanced security features
- ✅ Improved UI/UX with responsive design
- ✅ Background task processing with Celery
- ✅ Comprehensive API documentation

### Version 1.0.0
- ✅ Basic prediction system
- ✅ Career recommendations
- ✅ AI chat functionality
- ✅ Student dashboard
- ✅ Admin document upload
