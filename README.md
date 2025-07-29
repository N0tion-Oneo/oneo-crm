# Oneo CRM

A comprehensive, AI-powered Customer Relationship Management (CRM) system built with Django, featuring real-time collaboration, multi-tenant architecture, and intelligent workflow automation.

## 🚀 Features

### Core CRM Functionality
- **Multi-tenant Architecture**: Isolated tenant environments with custom domains
- **Real-time Collaboration**: Live updates, operational transforms, and SSE
- **AI Integration**: Intelligent routing, parallel processing, and cache optimization
- **Workflow Automation**: Visual workflow builder with AI-powered nodes
- **Relationship Engine**: Advanced relationship mapping and tracking
- **Pipeline Management**: Customizable sales and recruitment pipelines

### Advanced Features
- **Authentication & Authorization**: Role-based access control with session management
- **API Layer**: RESTful APIs with GraphQL support and auto-generated documentation
- **Communication Hub**: Multi-channel communication (Email, SMS, WhatsApp, LinkedIn)
- **Monitoring & Analytics**: Health checks, metrics, and performance monitoring
- **Recovery System**: Automated backup and disaster recovery
- **Content Management**: Dynamic content library and template system

## 🏗️ Architecture

```
Oneo CRM/
├── ai/                    # AI integration and processing
├── api/                   # REST API and GraphQL endpoints
├── authentication/        # User authentication and authorization
├── communications/        # Multi-channel communication system
├── core/                 # Core utilities and base models
├── monitoring/           # Health checks and metrics
├── pipelines/            # Sales and recruitment pipelines
├── realtime/            # Real-time collaboration features
├── relationships/        # Relationship mapping engine
├── tenants/             # Multi-tenant architecture
├── users/               # User management
└── workflows/           # Workflow automation engine
```

## 🛠️ Technology Stack

- **Backend**: Django 4.x with Python 3.9+
- **Database**: PostgreSQL with Redis for caching
- **Real-time**: WebSockets with Django Channels
- **AI/ML**: TinyLlama integration with intelligent routing
- **API**: REST + GraphQL with auto-generated documentation
- **Frontend**: React with Tailwind CSS (planned)
- **Deployment**: Docker-ready with comprehensive monitoring

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Node.js 16+ (for frontend development)

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd oneo-crm
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database and Redis settings
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/oneo_crm

# Redis
REDIS_URL=redis://localhost:6379/0

# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# AI Configuration
AI_MODEL_PATH=/path/to/tinyllama/model
AI_CACHE_ENABLED=True

# Communication APIs
EMAIL_BACKEND=smtp
SMS_PROVIDER=twilio
WHATSAPP_PROVIDER=meta
```

## 📚 API Documentation

- **REST API**: Available at `/api/docs/`
- **GraphQL**: Available at `/graphql/`
- **SDK Documentation**: Auto-generated SDKs in `/api/templates/api/sdk/`

## 🧪 Testing

Run the comprehensive test suite:

```bash
python manage.py test
```

## 📊 Monitoring

- **Health Checks**: `/health/`
- **Metrics**: `/metrics/`
- **Performance**: Real-time monitoring dashboard

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `/docs/` directory
- **Issues**: Report bugs and feature requests via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions and ideas

## 🗺️ Roadmap

- [ ] React frontend implementation
- [ ] Advanced AI features
- [ ] Mobile app development
- [ ] Enterprise features
- [ ] Third-party integrations

---

**Oneo CRM** - Empowering businesses with intelligent relationship management. 