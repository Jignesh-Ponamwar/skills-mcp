---
name: django-web-framework
description: Build web applications with Django - models, views, URL routing, middleware, Django ORM, authentication, testing, deployment, and best practices
license: Apache-2.0
metadata:
  author: Django Software Foundation
  version: 5.0
  tags: [django, python, web-framework, backend, orm, mvc]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - Django model
    - Django view
    - Django template
    - Django ORM
    - create Django app
    - Django middleware
    - Django authentication
    - Django testing
    - Django migration
    - Django form
  use_cases:
    - Build web applications with Python
    - Create REST APIs with Django REST Framework
    - Implement authentication and authorization
    - Manage databases with ORM
    - Deploy Django applications
  estimated_time: 20-30 minutes
  complexity_level: intermediate
  prerequisites:
    - Python 3.10+
    - Pip and virtual environments
    - Understanding of web frameworks
  source_url: https://docs.djangoproject.com
  last_updated: "2025-01-15"
---

# Django Web Framework

## Getting Started

Django is a high-level Python web framework that follows the Model-View-Template (MVT) pattern.

### Project Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Django
pip install django

# Create new project
django-admin startproject myproject
cd myproject

# Create new app
python manage.py startapp myapp
```

## Models (Database Layer)

Define your database schema using Django models:

```python
# myapp/models.py
from django.db import models

class Blog(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
```

### Migrations

Track database schema changes:

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration plan
python manage.py showmigrations
```

## Views (Business Logic)

Django supports class-based and function-based views:

### Function-Based Views

```python
# myapp/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Blog

def blog_list(request):
    blogs = Blog.objects.filter(published=True)
    return render(request, 'blog/list.html', {'blogs': blogs})

def blog_detail(request, pk):
    blog = get_object_or_404(Blog, pk=pk)
    return render(request, 'blog/detail.html', {'blog': blog})
```

### Class-Based Views

```python
from django.views import View
from django.views.generic import ListView, DetailView
from .models import Blog

class BlogListView(ListView):
    model = Blog
    template_name = 'blog/list.html'
    context_object_name = 'blogs'
    paginate_by = 10

    def get_queryset(self):
        return Blog.objects.filter(published=True)

class BlogDetailView(DetailView):
    model = Blog
    template_name = 'blog/detail.html'
```

## URL Routing

Map URLs to views:

```python
# myapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('blogs/', views.BlogListView.as_view(), name='blog-list'),
    path('blogs/<int:pk>/', views.BlogDetailView.as_view(), name='blog-detail'),
]

# myproject/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('myapp.urls')),
]
```

## Authentication

Built-in user authentication:

```python
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.models import User

# Create user
user = User.objects.create_user(username='john', password='secret123')

# Protect views
@login_required
def protected_view(request):
    return render(request, 'protected.html')

# In templates
{% if user.is_authenticated %}
    Welcome, {{ user.username }}!
{% else %}
    <a href="{% url 'login' %}">Login</a>
{% endif %}
```

## Django ORM Queries

Efficient database queries:

```python
# Basic queries
blogs = Blog.objects.all()
blog = Blog.objects.get(pk=1)
blogs = Blog.objects.filter(published=True)
blogs = Blog.objects.exclude(author='Anonymous')

# Aggregations
from django.db.models import Count, Q

count = Blog.objects.filter(published=True).count()
recent = Blog.objects.filter(created_at__gte='2025-01-01')
or_query = Blog.objects.filter(Q(published=True) | Q(author='Admin'))

# Relationships
author_blogs = Blog.objects.filter(author__isnull=False)
blog.related_set.all()

# Optimization
blogs = Blog.objects.select_related('author').all()
blogs = Blog.objects.prefetch_related('comments').all()
```

## Forms

Handle form validation:

```python
from django import forms
from .models import Blog

class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ['title', 'content', 'published']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
        }

# In view
def create_blog(request):
    if request.method == 'POST':
        form = BlogForm(request.POST)
        if form.is_valid():
            blog = form.save()
            return redirect('blog-detail', pk=blog.pk)
    else:
        form = BlogForm()
    return render(request, 'blog/form.html', {'form': form})
```

## Testing

Write tests for your Django app:

```python
# myapp/tests.py
from django.test import TestCase, Client
from .models import Blog

class BlogModelTest(TestCase):
    def setUp(self):
        self.blog = Blog.objects.create(title='Test', content='Content', author='Test')

    def test_blog_str(self):
        self.assertEqual(str(self.blog), 'Test')

class BlogViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.blog = Blog.objects.create(title='Test', published=True)

    def test_blog_list_view(self):
        response = self.client.get('/api/blogs/')
        self.assertEqual(response.status_code, 200)
```

Run tests:

```bash
python manage.py test
python manage.py test myapp.tests.BlogModelTest
python manage.py test --verbosity=2
```

## Django Admin

Auto-generated admin interface:

```python
# myapp/admin.py
from django.contrib import admin
from .models import Blog

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published', 'created_at')
    list_filter = ('published', 'created_at')
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'updated_at')
```

Access at: http://localhost:8000/admin

## Middleware

Process requests and responses:

```python
# myapp/middleware.py
class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        timezone.activate(request.user.timezone)
        response = self.get_response(request)
        return response

# Add to MIDDLEWARE in settings.py
MIDDLEWARE = [
    'myapp.middleware.TimezoneMiddleware',
]
```

## Static Files and Media

Handle CSS, JavaScript, and uploads:

```python
# settings.py
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# urls.py
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [...]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## Deployment

Production deployment checklist:

```python
# settings.py
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
SECRET_KEY = os.getenv('SECRET_KEY')

# Use environment-based settings
if os.getenv('ENVIRONMENT') == 'production':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
        }
    }

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Use gunicorn
pip install gunicorn
gunicorn myproject.wsgi:application
```

## Best Practices

1. **Use virtual environments** - Isolate project dependencies
2. **Version control** - Keep .gitignore updated (exclude venv/, db.sqlite3, .env)
3. **Environment variables** - Use python-dotenv for secrets
4. **Database indexes** - Add indexes to frequently queried fields
5. **Caching** - Use Django's cache framework for performance
6. **API pagination** - Limit response sizes
7. **Security** - CSRF protection, SQL injection prevention (built-in with ORM)
8. **Logging** - Configure logging for debugging in production
9. **CORS headers** - Handle cross-origin requests properly
10. **API versioning** - Plan for backward compatibility

---

Source: Django Official Documentation (https://docs.djangoproject.com)
